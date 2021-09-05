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

class Shloompy(sc2.BotAI):

    def __init__(self):
        super(Shloompy)
        self.army_gather_point = None
        self.rally_updated = False


    async def on_step(self, iteration: int):

        if iteration == 0:
            self.army_gather_point = self.main_base_ramp.protoss_wall_pylon

        await self.distribute_workers()
        await self.build_probes()
        await self.build_pylons()
        await self.build_assimilators()
        await self.follow_build()
        # await self.build_units()
        await self.research()


    ###########ACTIONS###########

    # async def distribute_workers(self):
    #     ass = self.structures(UnitTypeId.ASSIMILATOR)
    #     if ass:
    #         print(ass.random.assigned_harvesters)
    #
    #     if self.idle_worker_count:
    #         idle_probes = self.workers.filter(lambda probe: probe.is_idle)
    #

    async def build_probes(self):

        for nexus in self.townhalls.ready:
            if self.workers.amount < self.townhalls.amount * FULL_SATURATION and nexus.is_idle:
            # if nexus.is_idle:
                if self.can_afford(UnitTypeId.PROBE):
                    nexus.train(UnitTypeId.PROBE)

    async def build_pylons(self):

        if self.supply_used <= 60 and self.supply_left < 3:

            if self.already_pending(UnitTypeId.PYLON) == 0 and self.can_afford(UnitTypeId.PYLON):

                for nexus in self.townhalls:

                    await self.build(UnitTypeId.PYLON, near= nexus.position.towards(self.game_info.map_center, np.random.choice(10)))

        elif self.supply_used > 60 and self.supply_left < 7:

            if self.already_pending(UnitTypeId.PYLON) < 2 and self.can_afford(UnitTypeId.PYLON):

                for nexus in self.townhalls:

                    await self.build(UnitTypeId.PYLON, near= nexus.position.towards(self.game_info.map_center, np.random.choice(10)))

    async def build_assimilators(self):

        #first is right after gateway, second when starting CC
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

        #GENERIC BUILDING COMMAND
        # for nexus in self.townhalls.ready:
        #     geysers = self.vespene_geyser.closer_than(15, nexus)
        #     for geyser in geysers:
        #         if self.can_afford(UnitTypeId.ASSIMILATOR):
        #             worker = self.select_build_worker(geyser.position)
        #             if worker is None:
        #                 break
        #             if not self.gas_buildings or not self.gas_buildings.closer_than(1, geyser):
        #                 worker.build(UnitTypeId.ASSIMILATOR, geyser)
        #                 worker.stop(queue=True)

    async def follow_build(self):


        #TODO builds 3 gates

        if self.structures(UnitTypeId.PYLON).ready:
            pylon = self.structures(UnitTypeId.PYLON).ready.random

            #build cybernetics core if first gate is completed
            if self.already_pending(UnitTypeId.GATEWAY) == 1 and not self.structures(UnitTypeId.CYBERNETICSCORE):
                if self.can_afford(UnitTypeId.CYBERNETICSCORE) and not self.already_pending(UnitTypeId.CYBERNETICSCORE):
                    await self.build(UnitTypeId.CYBERNETICSCORE, near= pylon.position.towards(self.game_info.map_center, np.random.choice(3)))

            else:

                #build gateways up to 2
                if (self.can_afford(UnitTypeId.GATEWAY) and
                self.structures(UnitTypeId.GATEWAY).amount + self.already_pending(UnitTypeId.GATEWAY) < 2):

                    await self.build(UnitTypeId.GATEWAY, near=pylon.position.towards(self.game_info.map_center, np.random.choice(3)))
                    await self.set_rally_points()

                #take natural
                if (self.can_afford(UnitTypeId.NEXUS)
                    and self.structures(UnitTypeId.CYBERNETICSCORE)
                    and self.workers.amount > self.townhalls.amount * FULL_SATURATION - 6
                    and self.structures(UnitTypeId.NEXUS).amount < 3):

                    await self.expand_now()
                    await self.set_rally_points()

                #build robo facility
                elif (self.can_afford(UnitTypeId.ROBOTICSFACILITY)
                    and self.structures(UnitTypeId.WARPGATE).amount + self.structures(UnitTypeId.GATEWAY).amount < 3
                    and not self.structures(UnitTypeId.ROBOTICSFACILITY)
                    and not self.already_pending(UnitTypeId.ROBOTICSFACILITY)
                    and self.structures(UnitTypeId.NEXUS).amount > 1):

                    await self.build(UnitTypeId.ROBOTICSFACILITY, near= pylon.position.towards(self.game_info.map_center, np.random.choice(3)))



                #build twilight council
                elif (self.can_afford(UnitTypeId.TWILIGHTCOUNCIL)
                    and self.structures(UnitTypeId.ROBOTICSFACILITY).ready
                    and not self.structures(UnitTypeId.TWILIGHTCOUNCIL)
                    and not self.already_pending(UnitTypeId.TWILIGHTCOUNCIL)):
                    await self.set_rally_points()
                    await self.build(UnitTypeId.TWILIGHTCOUNCIL,near= pylon.position.towards(self.game_info.map_center, np.random.choice(3)))

                #build forge
                elif (self.can_afford(UnitTypeId.FORGE)
                    and (self.structures(UnitTypeId.TWILIGHTCOUNCIL).ready or self.already_pending(UnitTypeId.TWILIGHTCOUNCIL))
                    and self.structures(UnitTypeId.FORGE).amount < 2
                    and self.already_pending(UnitTypeId.FORGE) < 2):

                    await self.build(UnitTypeId.FORGE, near= pylon.position.towards(self.game_info.map_center, np.random.choice(3)))

                #add 2 more gates
                elif (self.can_afford(UnitTypeId.GATEWAY) and
                        self.structures(UnitTypeId.WARPGATE).amount + self.structures(UnitTypeId.GATEWAY).amount < 4
                        and self.structures(UnitTypeId.FORGE).ready):
                    await self.build(UnitTypeId.GATEWAY, near=pylon.position.towards(self.game_info.map_center, np.random.choice(3)))
                    await self.set_rally_points()

                #build templar archives
                elif (self.can_afford(UnitTypeId.TEMPLARARCHIVE)
                      and self.structures(UnitTypeId.TWILIGHTCOUNCIL).ready
                      and not self.structures(UnitTypeId.TEMPLARARCHIVE)
                      and not self.already_pending(UnitTypeId.TEMPLARARCHIVE)):

                    await self.build(UnitTypeId.TEMPLARARCHIVE,
                                     near=pylon.position.towards(self.game_info.map_center, np.random.choice(3)))

                #go to 12 gates
                elif (self.can_afford(UnitTypeId.GATEWAY) and
                        self.structures(UnitTypeId.WARPGATE).amount + self.structures(UnitTypeId.GATEWAY).amount < 12
                        and self.structures(UnitTypeId.NEXUS).amount > 2):
                    await self.build(UnitTypeId.GATEWAY, near=pylon.position.towards(self.game_info.map_center, np.random.choice(3)))
                    await self.set_rally_points()

    async def set_rally_points(self):


        if self.structures(UnitTypeId.NEXUS).amount == 2:
            self.army_gather_point = self.structures(UnitTypeId.NEXUS)[1].position.towards(self.game_info.map_center, 10)


        for gw in self.structures(UnitTypeId.GATEWAY):
            gw(AbilityId.SMART, self.army_gather_point)


        for rf in self.structures(UnitTypeId.ROBOTICSFACILITY):
            rf(AbilityId.SMART, self.army_gather_point)

    async def build_units(self):

        for gw in self.structures(UnitTypeId.GATEWAY).ready.idle:

            if self.can_afford(UnitTypeId.SENTRY) and (self.units(UnitTypeId.STALKER).amount > 1 or self.already_pending(UnitTypeId.STALKER)) and self.units(UnitTypeId.SENTRY).amount == 0:
                    gw.train(UnitTypeId.SENTRY)

            elif self.can_afford(UnitTypeId.STALKER):

                gw.train(UnitTypeId.STALKER)
        for rf in self.structures(UnitTypeId.ROBOTICSFACILITY).ready.idle:
            if self.can_afford(UnitTypeId.OBSERVER) and self.already_pending(UnitTypeId.OBSERVER) == 0 and self.units(UnitTypeId.OBSERVER).amount == 0:
                rf.train(UnitTypeId.OBSERVER)

            elif self.can_afford(UnitTypeId.IMMORTAL):
                rf.train(UnitTypeId.IMMORTAL)

    async def research(self):

        await self.twilight_research()
        await self.forge_research()

    async def twilight_research(self):

        tcs = self.structures(UnitTypeId.TWILIGHTCOUNCIL).ready
        for tc in tcs:
            if self.can_afford(AbilityId.RESEARCH_CHARGE) and not self.already_pending_upgrade(UpgradeId.CHARGE):
                tc.research(UpgradeId.CHARGE)

            elif self.already_pending_upgrade(UpgradeId.CHARGE) == 1 and self.can_afford(AbilityId.RESEARCH_BLINK):
                tc.research(UpgradeId.BLINKTECH)

    async def forge_research(self):

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
def main():
    sc2.run_game(
        sc2.maps.get("AcolyteLE"),
        [Bot(sc2.Race.Protoss, Shloompy()), Computer(sc2.Race.Terran, sc2.Difficulty.Hard)],
        realtime=False
    )

main()