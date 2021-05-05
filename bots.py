from pysc2.agents import base_agent
from pysc2.env import sc2_env, run_loop
from pysc2.lib import actions, features, units
from absl import app
import numpy as np
import random


class rlAgent(base_agent.BaseAgent):

    base_top_left = None
    actions = ("do_nothing",
               "harvest_minerals",
               "build_pylon",
               "build_gateway",
               "train_zealot",
               "attack")

    def step(self,obs):
        super(rlAgent, self).step(obs)

        if obs.first():
            nexus = self.get_my_units_by_type(obs, units.Protoss.Nexus)[0]
            self.base_top_left = (nexus.x < 32)
        pylons = self.get_my_completed_units_by_type(obs, units.Protoss.Pylon)
        gateways = self.get_my_completed_units_by_type(obs, units.Protoss.Gateway)
        if len(gateways) > 0:
            return self.train_zealots(obs)
        if len(pylons) > 0:
            return self.build_gateway(obs)
        else:
            return self.build_pylon(obs)
        # return actions.RAW_FUNCTIONS.no_op()


    #-----------------UTILITY----------------

    def get_my_units_by_type(self, obs, unit_type):

        return [unit for unit in obs.observation.raw_units if unit.unit_type == unit_type and
                unit.alliance == features.PlayerRelative.SELF]

    def get_my_completed_units_by_type(self, obs, unit_type):
        return [unit for unit in obs.observation.raw_units
                if unit.unit_type == unit_type and
                unit.build_progress == 100 and
                unit.alliance == features.PlayerRelative.SELF]

    def get_enemy_units_by_type(self, obs, unit_type):
        return [unit for unit in obs.observation.raw_units
                if unit.unit_type == unit_type
                and unit.alliance == features.PlayerRelative.ENEMY]

    def get_enemy_completed_units_by_type(self, obs, unit_type):
        return [unit for unit in obs.observation.raw_units
                if unit.unit_type == unit_type
                and unit.build_progress == 100
                and unit.alliance == features.PlayerRelative.ENEMY]

    def get_distances(self, obs, units, xy):
        units_xy = [(unit.x, unit.y) for unit in units]
        return np.linalg.norm(np.array(units_xy) - np.array(xy), axis=1)


    #-----------------ACTIONS----------------

    def do_nothing(self, obs):
        return actions.RAW_FUNCTIONS.no_op()

    def harvest_minerals(self, obs):

        probes = self.get_my_units_by_type(obs, units.Protoss.Probe)
        idle_probes = [probe for probe in probes if probe.order_length == 0]
        if idle_probes:
            mineral_patches = [unit for unit in obs.observation.raw_units
                         if unit.unit_type in [
                           units.Neutral.BattleStationMineralField,
                           units.Neutral.BattleStationMineralField750,
                           units.Neutral.LabMineralField,
                           units.Neutral.LabMineralField750,
                           units.Neutral.MineralField,
                           units.Neutral.MineralField750,
                           units.Neutral.PurifierMineralField,
                           units.Neutral.PurifierMineralField750,
                           units.Neutral.PurifierRichMineralField,
                           units.Neutral.PurifierRichMineralField750,
                           units.Neutral.RichMineralField,
                           units.Neutral.RichMineralField750
                         ]]
            probe = random.choice(idle_probes)
            distances = self.get_distances(obs, mineral_patches, (probe.x, probe.y))
            patch = mineral_patches[np.argmin(distances)]
            return actions.RAW_FUNCTIONS.Harvest_Gather_unit("now", probe.tag, patch.tag)

    def build_pylon(self, obs):

        pylons = self.get_my_units_by_type(obs, units.Protoss.Pylon)
        probes = self.get_my_units_by_type(obs, units.Protoss.Probe)
        free_supply = obs.observation.player.food_cap - obs.observation.player.food_used

        if len(pylons) == 0 and obs.observation.player.minerals >= 100 and probes:
            pylon_xy = (22, 26) if self.base_top_left else (35, 42)
            distances = self.get_distances(obs, probes, pylon_xy)
            probey = probes[np.argmin(distances)]
            return actions.RAW_FUNCTIONS.Build_Pylon_pt("now", probey.tag, pylon_xy)
        return actions.RAW_FUNCTIONS.no_op()

    def build_gateway(self, obs):

        completed_pylons = self.get_my_completed_units_by_type(obs, units.Protoss.Pylon)
        gateways = self.get_my_completed_units_by_type(obs,units.Protoss.Gateway)
        probes = self.get_my_units_by_type(obs, units.Protoss.Probe)
        if (len(completed_pylons) > 0 and len(gateways) == 0 and obs.observation.player.minerals >= 150 and len(probes) > 0):
            gateway_xy = (22, 21) if self.base_top_left else (35, 45)
            distances = self.get_distances(obs,probes, gateway_xy)
            probe = probes[np.argmin(distances)]
            return actions.RAW_FUNCTIONS.Build_Gateway_pt("now", probe.tag, gateway_xy)
        return actions.RAW_FUNCTIONS.no_op()

    def train_zealots(self, obs):

        completed_gateways = self.get_my_completed_units_by_type(obs, units.Protoss.Gateway)
        free_supply = obs.observation.player.food_cap - obs.observation.player.food_used
        if len(completed_gateways) > 0 and obs.observation.player.minerals >= 100 and free_supply > 1:
            gateway = self.get_my_units_by_type(obs, units.Protoss.Gateway)[0]
            if gateway.order_length < 5:
                return actions.RAW_FUNCTIONS.Train_Zealot_quick("now", gateway.tag)
        return actions.RAW_FUNCTIONS.no_op()


class ProtossAgent(base_agent.BaseAgent):

    def __init__(self):
        super(ProtossAgent, self).__init__()
        self.base_top_left = None

    def unit_type_is_selected(self, obs, unit_type):
        if (len(obs.observation.single_select) > 0 and
                obs.observation.single_select[0].unit_type == unit_type):
            return True

        if (len(obs.observation.multi_select) > 0 and
                obs.observation.multi_select[0].unit_type == unit_type):
            return True

        return False

    def get_my_units_by_type(self, obs, unit_type):

        return [unit for unit in obs.observation.raw_units if unit.unit_type == unit_type and
                unit.alliance == features.PlayerRelative.SELF]

    def get_distances(self, obs, units, xy):
        units_xy = [(unit.x, unit.y) for unit in units]
        return np.linalg.norm(np.array(units_xy) - np.array(xy), axis=1)

    # def build_pylon(self, obs):

    def get_my_completed_units_by_type(self, obs, unit_type):
        return [unit for unit in obs.observation.raw_units
                if unit.unit_type == unit_type and
                unit.build_progress == 100 and
                unit.alliance == features.PlayerRelative.SELF]

    def build_pylon(self, obs, pylon_xy):

        probes = self.get_my_units_by_type(obs, units.Protoss.Probe)
        if len(probes) > 0:

            distances = self.get_distances(obs, probes, pylon_xy)
            probe = probes[np.argmin(distances)]
            return actions.RAW_FUNCTIONS.Build_Pylon_pt("now", probe.tag, pylon_xy)


    def build_gateway(self, obs):

        probes = self.get_my_units_by_type(obs, units.Protoss.Probe)
        if len(probes) > 0:
            gateway_xy = (22, 24) if self.base_top_left else (35, 45)
            distances = self.get_distances(obs, probes, gateway_xy)
            probe = probes[np.argmin(distances)]
            return actions.RAW_FUNCTIONS.Build_Gateway_pt("now", probe.tag, gateway_xy)

    def step(self,obs):
        super(ProtossAgent, self).step(obs)

        if obs.first():
            nexus = self.get_my_units_by_type(obs, units.Protoss.Nexus)[0]
            self.base_top_left = (nexus.x < 32)

        pylons = self.get_my_units_by_type(obs, units.Protoss.Pylon)
        pylon_xy = (22, 20) if self.base_top_left else (35, 42)
        if len(pylons) == 0 and obs.observation.player.minerals >= 100:
            return self.build_pylon(obs, pylon_xy)


        completed_pylons = self.get_my_completed_units_by_type(obs, units.Protoss.Pylon)
        gateways = self.get_my_completed_units_by_type(obs, units.Protoss.Gateway)

        if len(completed_pylons) > 0 and len(gateways) == 0 and obs.observation.player.minerals >= 150:
            return self.build_gateway(obs)


        completed_gateways = self.get_my_completed_units_by_type(obs, units.Protoss.Gateway)
        free_supply = obs.observation.player.food_cap - obs.observation.player.food_used
        # if obs.observation.player.idle_worker_count > 0
        # if free_supply <= 2 and obs.observation.player.idle:
        #     offset_x = random.randint(-4,4)
        #     offset_y = random.randint(-4, 4)
        #     return self.build_pylon(obs, (pylon_xy[0] + offset_x, pylon_xy[1] + offset_y))

        if len(completed_gateways) > 0 and obs.observation.player.minerals >= 100 and free_supply >= 2:
            gateway = gateways[0]
            if gateway.order_length < 5:
                return actions.RAW_FUNCTIONS.Train_Zealot_quick("now", gateway.tag)

        zealots = self.get_my_units_by_type(obs, units.Protoss.Zealot)
        if len(zealots) > 4:
            attack_xy = (38,44) if self.base_top_left else (19, 23)
            distances = self.get_distances(obs, zealots, attack_xy)
            zealot = zealots[np.argmax(distances)] #Selects furthest zealot
            x_offset = random.randint(-4, 4)
            y_offset = random.randint(-4, 4)
            return actions.RAW_FUNCTIONS.Attack_pt("now", zealot.tag,
                                                   (attack_xy[0] + x_offset, attack_xy[1] + y_offset))
        return actions.RAW_FUNCTIONS.no_op()




def main(unused_argv):
    agent = rlAgent()
    try:
        while True:
            with sc2_env.SC2Env(
                    map_name="Simple64",
                    players=[sc2_env.Agent(sc2_env.Race.protoss),
                             sc2_env.Bot(sc2_env.Race.protoss,
                                         sc2_env.Difficulty.very_easy)],
                    agent_interface_format=features.AgentInterfaceFormat(
                        action_space=actions.ActionSpace.RAW,
                        use_raw_units=True,
                        raw_resolution=64,
                        feature_dimensions=features.Dimensions(screen=84, minimap=64)
                    ),
            visualize=True) as env:
                run_loop.run_loop([agent], env)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    app.run(main)