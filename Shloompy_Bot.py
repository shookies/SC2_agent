import sc2
from sc2.bot_ai import BotAI
import sc2.game_info
from sc2.player import Bot, Computer
from sc2.unit import Unit
from sc2 import units
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
import numpy as np

FULL_SATURATION = 22

DESIRED_ARCHON_RATIO = 0.25
DESIRED_IMMORTAL_RATIO = 0.25
DESIRED_ZEALOT_RATIO = 0.4
DESIRED_STALKER_RATIO = 0.1
MAX_PROBES = 70

class Shloompy(sc2.BotAI):

    def __init__(self):
        super(Shloompy)
        self.army_gather_point = None
        self.rally_updated = False


    async def on_step(self, iteration: int):
        '''
        A step is when the agent makes a decision. The plan is to follow a certain build order, expand when needed and
        get a large chunk of zealots, archons and immortals and attack the enemy main base.
        :param iteration:
        :return:
        '''
        if iteration == 0:
            self.army_gather_point = self.main_base_ramp.protoss_wall_pylon

        await self.distribute_workers()
        await self.build_probes()
        await self.build_pylons()
        await self.build_assimilators()
        await self.follow_build()
        await self.train_army()
        await self.research()
        await self.move_army()


    ###########ACTIONS###########



    async def build_probes(self):
        '''
        Builds probes until full saturation or until 70 probes are working.
        :return:
        '''
        for nexus in self.townhalls.ready:
            if self.workers.amount < self.townhalls.amount * FULL_SATURATION and self.workers.amount < MAX_PROBES and nexus.is_idle:
            # if nexus.is_idle:
                if self.can_afford(UnitTypeId.PROBE):
                    nexus.train(UnitTypeId.PROBE)

    async def build_pylons(self):
        '''
        Builds pylons near the agent's nexii
        :return:
        '''

        #Build 1 pylon if we're under 60 supply
        if self.supply_used <= 60 and self.supply_left < 3:

            if self.already_pending(UnitTypeId.PYLON) == 0 and self.can_afford(UnitTypeId.PYLON):

                for nexus in self.townhalls:

                    await self.build(UnitTypeId.PYLON, near= nexus.position.towards(self.game_info.map_center, np.random.choice(10)))

        #If we're over 60 supply we can build 2 pylons at the same time
        elif self.supply_used > 60 and self.supply_left < 7:

            if self.already_pending(UnitTypeId.PYLON) < 2 and self.can_afford(UnitTypeId.PYLON):

                for nexus in self.townhalls:

                    await self.build(UnitTypeId.PYLON, near= nexus.position.towards(self.game_info.map_center, np.random.choice(10)))

    async def build_assimilators(self):
        '''
        Builds assimilators. First one is built right after gateway. Second one is when starting the CyberCore
        :return:
        '''

        if (self.structures(UnitTypeId.GATEWAY).amount == 1 and not self.gas_buildings) or \
                (self.structures(UnitTypeId.GATEWAY).amount == 2):
            for nexus in self.townhalls.ready:
                geyser = self.vespene_geyser.closer_than(15,nexus).random

                if self.can_afford(UnitTypeId.ASSIMILATOR):
                    worker = self.select_build_worker(geyser.position)
                    if worker is None:
                        break
                    if not self.gas_buildings or not self.gas_buildings.closer_than(1, geyser):
                        worker.build(UnitTypeId.ASSIMILATOR, geyser)
                        worker.stop(queue=True)



    async def follow_build(self):
        '''
        Follows a scripted build order:

        Pylon
        Gateway
        Cybernetics Core
        Gateway
        Expansion at Natural
        Robotics Facility
        Twilight Council
        Forge
        Gateway x2
        Templar Archives
        Gateway x12
        :return:
        '''

        STEP = 4

        if self.structures(UnitTypeId.PYLON).ready:
            pylon = self.structures(UnitTypeId.PYLON).ready.random

            #build cybernetics core if first gate is completed
            if self.already_pending(UnitTypeId.GATEWAY) == 1 and not self.structures(UnitTypeId.CYBERNETICSCORE):
                if self.can_afford(UnitTypeId.CYBERNETICSCORE) and not self.already_pending(UnitTypeId.CYBERNETICSCORE):
                    await self.build(UnitTypeId.CYBERNETICSCORE, near= pylon.position.towards(self.game_info.map_center, np.random.choice(3)),placement_step= STEP)

            else:

                #build gateways up to 2
                if (self.can_afford(UnitTypeId.GATEWAY) and
                self.structures(UnitTypeId.GATEWAY).amount + self.already_pending(UnitTypeId.GATEWAY) < 2):

                    await self.build(UnitTypeId.GATEWAY, near=pylon.position.towards(self.game_info.map_center, np.random.choice(3)),placement_step= STEP)
                    # await self.set_rally_points()



                #expand
                if (self.can_afford(UnitTypeId.NEXUS)
                    and self.structures(UnitTypeId.CYBERNETICSCORE)
                    and self.workers.amount > self.townhalls.amount * FULL_SATURATION - 6
                    and self.structures(UnitTypeId.NEXUS).amount < 4):

                    #Set army_gather_point to the natural ramp in order to defend the base
                    first_nexus = self.townhalls.first
                    natural_ramp = sorted(self.game_info.map_ramps, key= lambda ramp: ramp.top_center.distance_to(first_nexus))
                    self.army_gather_point = natural_ramp[1].top_center
                    await self.expand_now()


                #build robo facility
                elif (self.can_afford(UnitTypeId.ROBOTICSFACILITY)
                    and self.structures(UnitTypeId.WARPGATE).amount + self.structures(UnitTypeId.GATEWAY).amount < 3
                    and not self.structures(UnitTypeId.ROBOTICSFACILITY)
                    and not self.already_pending(UnitTypeId.ROBOTICSFACILITY)
                    and self.structures(UnitTypeId.NEXUS).amount > 1):

                    await self.build(UnitTypeId.ROBOTICSFACILITY, near= pylon.position.towards(self.game_info.map_center, np.random.choice(3)),placement_step= STEP)
                    #todo set robo rally point?


                #build twilight council
                elif (self.can_afford(UnitTypeId.TWILIGHTCOUNCIL)
                    and self.structures(UnitTypeId.ROBOTICSFACILITY).ready
                    and not self.structures(UnitTypeId.TWILIGHTCOUNCIL)
                    and not self.already_pending(UnitTypeId.TWILIGHTCOUNCIL)):

                    await self.build(UnitTypeId.TWILIGHTCOUNCIL,near= pylon.position.towards(self.game_info.map_center, np.random.choice(3)),placement_step= STEP)

                #build forge
                elif (self.can_afford(UnitTypeId.FORGE)
                    and (self.structures(UnitTypeId.TWILIGHTCOUNCIL).ready or self.already_pending(UnitTypeId.TWILIGHTCOUNCIL))
                    and self.structures(UnitTypeId.FORGE).amount < 2
                    and self.already_pending(UnitTypeId.FORGE) < 2):

                    await self.build(UnitTypeId.FORGE, near= pylon.position.towards(self.game_info.map_center, np.random.choice(3)),placement_step= STEP)

                #add 2 more gates
                elif (self.can_afford(UnitTypeId.GATEWAY) and
                        self.structures(UnitTypeId.WARPGATE).amount + self.structures(UnitTypeId.GATEWAY).amount < 4
                        and self.structures(UnitTypeId.FORGE).ready):

                    await self.build(UnitTypeId.GATEWAY, near=pylon.position.towards(self.game_info.map_center, np.random.choice(3)),placement_step= STEP)


                #build templar archives
                elif (self.can_afford(UnitTypeId.TEMPLARARCHIVE)
                      and self.structures(UnitTypeId.TWILIGHTCOUNCIL).ready
                      and not self.structures(UnitTypeId.TEMPLARARCHIVE)
                      and not self.already_pending(UnitTypeId.TEMPLARARCHIVE)):

                    await self.build(UnitTypeId.TEMPLARARCHIVE,
                                     near=pylon.position.towards(self.game_info.map_center, np.random.choice(3)),placement_step= STEP)

                #go to 12 gates
                elif (self.structures(UnitTypeId.TEMPLARARCHIVE).ready
                    and self.can_afford(UnitTypeId.GATEWAY)
                    and self.structures(UnitTypeId.WARPGATE).amount + self.structures(UnitTypeId.GATEWAY).amount < 12
                    and self.structures(UnitTypeId.NEXUS).amount > 2):

                    await self.build(UnitTypeId.GATEWAY, near=pylon.position.towards(self.game_info.map_center, np.random.choice(3)),placement_step= STEP)


    # async def set_rally_points(self):
    #
    #
    #     if self.structures(UnitTypeId.NEXUS).amount == 2:
    #         self.army_gather_point = self.structures(UnitTypeId.NEXUS)[1].position.towards(self.game_info.map_center, 10)
    #
    #
    #     for gw in self.structures(UnitTypeId.GATEWAY):
    #         gw(AbilityId.SMART, self.army_gather_point)
    #
    #
    #     for rf in self.structures(UnitTypeId.ROBOTICSFACILITY):
    #         rf(AbilityId.SMART, self.army_gather_point)

    async def build_starter_units(self):
        '''
        Builds units until Warpgate research is done
        :return:
        '''
        for gw in self.structures(UnitTypeId.GATEWAY).ready.idle:

            if self.can_afford(UnitTypeId.SENTRY) and (self.units(UnitTypeId.STALKER).amount > 1 or self.already_pending(UnitTypeId.STALKER)) and self.units(UnitTypeId.SENTRY).amount == 0:
                    gw.train(UnitTypeId.SENTRY)

            elif self.can_afford(UnitTypeId.STALKER):

                gw.train(UnitTypeId.STALKER)

    async def research(self):
        '''

        :return:
        '''
        await self.warpgate_research()
        await self.twilight_research()
        await self.forge_research()

    async def warpgate_research(self):
        '''

        :return:
        '''
        if self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH) > 0:
            return
        else:
            if self.can_afford(AbilityId.RESEARCH_WARPGATE):
                ccs = self.structures(UnitTypeId.CYBERNETICSCORE).ready
                for cc in ccs:
                    cc.research(UpgradeId.WARPGATERESEARCH)

    async def twilight_research(self):
        '''

        :return:
        '''
        tcs = self.structures(UnitTypeId.TWILIGHTCOUNCIL).ready
        for tc in tcs:
            if self.can_afford(AbilityId.RESEARCH_CHARGE) and not self.already_pending_upgrade(UpgradeId.CHARGE):
                tc.research(UpgradeId.CHARGE)

            elif self.already_pending_upgrade(UpgradeId.CHARGE) == 1 and self.can_afford(AbilityId.RESEARCH_BLINK):
                tc.research(UpgradeId.BLINKTECH)

    async def forge_research(self):
        '''
        Upgrades ground weapons first, then ground armor.
        :return:
        '''
        forges = self.structures(UnitTypeId.FORGE).ready
        if not forges:
            return
        w1 = self.already_pending_upgrade(UpgradeId.PROTOSSGROUNDWEAPONSLEVEL1)
        w2 = self.already_pending_upgrade(UpgradeId.PROTOSSGROUNDWEAPONSLEVEL2)
        w3 = self.already_pending_upgrade(UpgradeId.PROTOSSGROUNDWEAPONSLEVEL3)

        a1 = self.already_pending_upgrade(UpgradeId.PROTOSSGROUNDARMORSLEVEL1)
        a2 = self.already_pending_upgrade(UpgradeId.PROTOSSGROUNDARMORSLEVEL2)
        a3 = self.already_pending_upgrade(UpgradeId.PROTOSSGROUNDARMORSLEVEL3)

        for forge in forges:
            if forge.is_idle:
                if not w1:
                    if self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1):
                        forge.research(UpgradeId.PROTOSSGROUNDWEAPONSLEVEL1)
                    else:
                        return

                elif not w2:
                    if self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2):
                        forge.research(UpgradeId.PROTOSSGROUNDWEAPONSLEVEL2)
                    else:
                        return  #TODO break instead of return? (case where cant afford w2 but can upgrade a1)

                elif not w3:
                    if self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3):
                        forge.research(UpgradeId.PROTOSSGROUNDWEAPONSLEVEL3)
                    else:
                        return

                if not a1:
                    if self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1):
                        forge.research(UpgradeId.PROTOSSGROUNDARMORSLEVEL1)
                    else:
                        return

                elif not a2:
                    if self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2):
                        forge.research(UpgradeId.PROTOSSGROUNDARMORSLEVEL2)
                    else:
                        return  # TODO break instead of return? (case where cant afford w2 but can upgrade a1)

                elif not a3:
                    if self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3):
                        forge.research(UpgradeId.PROTOSSGROUNDARMORSLEVEL3)
                    else:
                        return

    async def select_warp_in_pylon(self):
        """
        selects the outermost nexus and finds a pylon closest to it
        :return: the selected pylon Unit ID
        """
        last_nexus = self.townhalls[-1]
        pylons = sorted(self.structures(UnitTypeId.PYLON).ready, key= lambda py: py.distance_to(last_nexus))
        if pylons:
            return pylons[0]

        return None

    async def warp_in_unit(self, AID, UID):
        """

        :param AID: Ability ID of warping in the unit (for warpgate)
        :param UID: Unit ID (for warp in command)
        :return:
        """

        for warpgate in self.structures(UnitTypeId.WARPGATE).ready:
            abilities = await self.get_available_abilities(warpgate)

            if AID in abilities:
                pylon = await self.select_warp_in_pylon()
                if pylon is None:
                    return
                pos = pylon.position.random_on_distance(4)
                placement = await self.find_placement(AID, pos, placement_step= 1)
                if placement is None:
                    print("Can't find warp in placement")
                    return
                warpgate.warp_in(UID, placement)

    async def evaluate_army_composition(self):
        '''
        Evaluates how much of each unit we have in the army. The agent builds units according to a predetermined
        army composition ( A ratio of Immortals, Archons, Zealots, Stalkers)
        :return:
        '''
        army = self.units.not_structure.exclude_type(UnitTypeId.PROBE)
        army_size = army.amount
        archon_size = army(UnitTypeId.ARCHON).ready.amount
        immortal_size = army(UnitTypeId.IMMORTAL).amount
        zealot_size = army(UnitTypeId.ZEALOT).amount
        stalker_size = army(UnitTypeId.STALKER).amount

        archon_ratio = 0 if archon_size == 0 else archon_size / army_size
        immortal_ratio = 0 if immortal_size == 0 else immortal_size / army_size
        zealot_ratio = 0 if zealot_size == 0 else zealot_size / army_size
        stalker_ratio = 0 if stalker_size == 0 else stalker_size / army_size
        # print("army size " + str(army_size) + ", archons " + str(archon_size) + ", immorties " + str(immortal_size) + ", zealotbois " + str(zealot_size) + ", stalkers " + str(stalker_size))
        return [archon_ratio, stalker_ratio, zealot_ratio, immortal_ratio]


    async def train_army(self):
        '''
        Trains units according to the predetermined ratio. Prioritizes Immortals and Archons.
        :return:
        '''

        if self.structures(UnitTypeId.GATEWAY).ready.idle:
            await self.build_starter_units()

        templars = self.units(UnitTypeId.HIGHTEMPLAR)
        for ht in templars:
            ht(AbilityId.MORPH_ARCHON)

        archon_ratio, stalker_ratio, zealot_ratio, immortal_ratio = await self.evaluate_army_composition()

        if self.can_afford(UnitTypeId.OBSERVER) and self.already_pending(UnitTypeId.OBSERVER) == 0 and self.units(UnitTypeId.OBSERVER).amount == 0:
            if self.structures(UnitTypeId.ROBOTICSFACILITY).ready.idle:
                self.structures(UnitTypeId.ROBOTICSFACILITY).random.train(UnitTypeId.OBSERVER)

        if immortal_ratio < DESIRED_IMMORTAL_RATIO:
            if self.structures(UnitTypeId.ROBOTICSFACILITY).ready:
                for rf in self.structures(UnitTypeId.ROBOTICSFACILITY).idle:
                    if self.can_afford(UnitTypeId.IMMORTAL):
                        rf.train(UnitTypeId.IMMORTAL)

        if  archon_ratio < DESIRED_ARCHON_RATIO:

            if self.structures(UnitTypeId.WARPGATE).ready.idle:
                if self.can_afford(UnitTypeId.HIGHTEMPLAR):
                    await self.warp_in_unit(AbilityId.WARPGATETRAIN_HIGHTEMPLAR, UnitTypeId.HIGHTEMPLAR)

        if stalker_ratio < DESIRED_STALKER_RATIO or not self.structures(UnitTypeId.ROBOTICSFACILITY):
            if self.can_afford(UnitTypeId.STALKER):
                await self.warp_in_unit(AbilityId.WARPGATETRAIN_STALKER, UnitTypeId.STALKER)

        if zealot_ratio < DESIRED_ZEALOT_RATIO:
            if self.can_afford(UnitTypeId.ZEALOT) and self.already_pending_upgrade(UpgradeId.CHARGE) == 1:
                await self.warp_in_unit(AbilityId.WARPGATETRAIN_ZEALOT, UnitTypeId.ZEALOT)


    async def move_army(self):
        '''
        A simple army management function. If army supply < 80 we move all units to the army_gather_point. Otherwise we
        attack the enemy position
        :return:
        '''
        army = self.units.not_structure.exclude_type(UnitTypeId.PROBE)

        if self.supply_army > 80:
            for unit in army:
                if unit.type_id == UnitTypeId.HIGHTEMPLAR:
                    unit(AbilityId.MORPH_ARCHON)
                else:
                    unit.attack(self.enemy_start_locations[0])

        else:
            if int(self.time) % 12 == 0:

                for unit in army:
                    unit.move(self.army_gather_point)

def main():
    sc2.run_game(
        sc2.maps.get("AbyssalReefLE"),
        [Bot(sc2.Race.Protoss, Shloompy()), Computer(sc2.Race.Terran, sc2.Difficulty.Hard)],
        realtime=False
    )

main()
