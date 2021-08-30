from pysc2.agents import base_agent
from pysc2.env import sc2_env, run_loop
from pysc2.lib import actions, features, units
from absl import app
import numpy as np
import pandas as pd
import random

class QLearningTable:

    def __init__(self, actions, learning_rate=0.01, discount_factor=0.9):
        self.actions = actions
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.q_table = pd.DataFrame(columns=self.actions, dtype=np.float64)

    def check_if_state_exists(self, state):

        if state not in self.q_table.index:
            self.q_table = self.q_table.append(pd.Series([0] * len(self.actions),
                                                         index=self.q_table.columns,
                                                         name=state))

    def choose_action(self, obs, epsilon = 0.9):
        self.check_if_state_exists(obs)
        if np.random.uniform() < epsilon:
            state_action = self.q_table.loc[obs, :]
            action = np.random.choice(state_action[state_action == np.max(state_action)].index) #TODO understand why index
        else:
            action = np.random.choice(self.actions)
        return action

    def learn(self, prev_state, action, reward, state):

        self.check_if_state_exists(state)
        q_predict = self.q_table.loc[prev_state, action]
        if state != 'terminal':
            q_estimate = reward + self.discount_factor * self.q_table.loc[state, :].max()
        else:
            q_estimate = reward

        self.q_table.loc[prev_state, action] += self.learning_rate * (q_estimate - q_predict)


class ProtossAgent(base_agent.BaseAgent):

    def __init__(self):
        super(ProtossAgent, self).__init__()
        self.base_top_left = None
        # self.actions = ("do_nothing",
        #                 "harvest_minerals",
        #                 "build_pylon",
        #                 "build_gateway",
        #                 "train_zealot",
        #                 "attack")
        self.actions = ["train_probe", "build_pylon", "build_gateway", "build_assimilator","harvest_gas", "harvest_minerals", "train_zealot", "attack", "build_cyber_core", "train_stalker"]
        self.pylon_coords = []
        # self.pylon_index = 0

    def step(self, obs):
        super(ProtossAgent, self).step(obs)

        if obs.first():
            nexus = self.get_my_units_by_type(obs, units.Protoss.Nexus)[0]
            self.base_top_left = True if nexus.x < 32 else False
            self.pylon_coords = [(22, 27), (23, 24), (25, 20)] if self.base_top_left else [(35, 40), (32, 46), (32, 42)]
            # self.pylon_coords = [(25, 29), (19, 29)] if self.base_top_left else [(32, 46), (38, 47)]

        return actions.RAW_FUNCTIONS.no_op()

    # -----------------UTILITY----------------

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

    def select_build_worker(self, obs, x, y):

        probes = self.get_my_completed_units_by_type(obs, units.Protoss.Probe)

        if probes:
            distances_to_point = self.get_distances(obs, probes, (x, y))
            min_index = np.argmin(distances_to_point)
            # probe = np.random.choice(probes[min_index])
            probe = probes[min_index]
            return probe
        return None


    # -----------------ACTIONS----------------

    def do_nothing(self, obs):
        return actions.RAW_FUNCTIONS.no_op()

    def train_probe(self, obs):

        free_supply = obs.observation.player.food_cap - obs.observation.player.food_used
        nexuses = self.get_my_completed_units_by_type(obs, units.Protoss.Nexus)
        if obs.observation.player.minerals >= 50 and free_supply > 0 and len(nexuses) > 0:
            nexus = nexuses[0]
            if nexus.order_length < 5:
                return actions.RAW_FUNCTIONS.Train_Probe_quick("now", nexus.tag)
        return actions.RAW_FUNCTIONS.no_op()

    def harvest_gas(self, obs):

        probes = self.get_my_units_by_type(obs, units.Protoss.Probe)
        nexus = self.get_my_units_by_type(obs, units.Protoss.Nexus)[0]
        idle_probes = [probe for probe in probes if probe.order_length == 0]
        extra_workers = (nexus.assigned_harvesters > nexus.ideal_harvesters)
        assimilators = self.get_my_completed_units_by_type(obs, units.Protoss.Assimilator)

        probe = random.choice(probes)
        if idle_probes:
            probe = random.choice(idle_probes)
        if extra_workers:
            x = 0

        if len(assimilators) > 0:
            assimilator = assimilators[0]   #TODO fix mining from both assimilators
            if assimilator.assigned_harvesters < 3:
                return actions.RAW_FUNCTIONS.Harvest_Gather_unit("now", probe.tag, assimilator.tag)

        return actions.RAW_FUNCTIONS.no_op()


    def build_assimilator(self, obs):

        geysers = [unit for unit in obs.observation.raw_units if unit.unit_type in [units.Neutral.VespeneGeyser]]
        nexus = self.get_my_units_by_type(obs, units.Protoss.Nexus)[0]
        distances = self.get_distances(obs, geysers, (nexus.x, nexus.y))
        geyser = geysers[np.argmin(distances)]

        probe = self.select_build_worker(obs, geyser.x, geyser.y)

        if obs.observation.player.minerals >= 75 and probe.any():
            return actions.RAW_FUNCTIONS.Build_Assimilator_unit("now", probe.tag, geyser.tag)

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
        return actions.RAW_FUNCTIONS.no_op()

    def build_pylon(self, obs):

        probes = self.get_my_units_by_type(obs, units.Protoss.Probe)
        pylons = self.get_my_units_by_type(obs, units.Protoss.Pylon)
        pylons_active = len(pylons)
        # print("pylons active: " + str(pylons_active))

        if obs.observation.player.minerals >= 100 and probes and pylons_active < 3:
            pylon_xy = self.pylon_coords[pylons_active]

            distances = self.get_distances(obs, probes, pylon_xy)
            probey = probes[np.argmin(distances)]
            return actions.RAW_FUNCTIONS.Build_Pylon_pt("now", probey.tag, pylon_xy)
        return actions.RAW_FUNCTIONS.no_op()

    def build_gateway(self, obs):

        completed_pylons = self.get_my_completed_units_by_type(obs, units.Protoss.Pylon)
        gateways = self.get_my_completed_units_by_type(obs, units.Protoss.Gateway)
        probes = self.get_my_units_by_type(obs, units.Protoss.Probe)
        if (len(completed_pylons) > 0 and len(gateways) == 0 and obs.observation.player.minerals >= 150 and len(
                probes) > 0):
            gateway_xy = (22, 21) if self.base_top_left else (35, 45)
            distances = self.get_distances(obs, probes, gateway_xy)
            probe = probes[np.argmin(distances)]
            return actions.RAW_FUNCTIONS.Build_Gateway_pt("now", probe.tag, gateway_xy)
        return actions.RAW_FUNCTIONS.no_op()

    def build_cyber_core(self, obs):

        completed_pylons = self.get_my_completed_units_by_type(obs, units.Protoss.Pylon)
        gateways = self.get_my_completed_units_by_type(obs, units.Protoss.Gateway)
        probes = self.get_my_units_by_type(obs, units.Protoss.Probe)
        if (len(completed_pylons) > 0 and len(gateways) > 0 and obs.observation.player.minerals >= 150 and len(
                probes) > 0):
            core_xy = (26, 22) if self.base_top_left else (33, 44)
            distances = self.get_distances(obs, probes, core_xy)
            probe = probes[np.argmin(distances)]
            return actions.RAW_FUNCTIONS.Build_CyberneticsCore_pt("now", probe.tag, core_xy)
        return actions.RAW_FUNCTIONS.no_op()

    def train_zealot(self, obs):

        completed_gateways = self.get_my_completed_units_by_type(obs, units.Protoss.Gateway)
        free_supply = obs.observation.player.food_cap - obs.observation.player.food_used
        if len(completed_gateways) > 0 and obs.observation.player.minerals >= 100 and free_supply > 1:
            gateway = self.get_my_units_by_type(obs, units.Protoss.Gateway)[0]
            if gateway.order_length < 5:
                return actions.RAW_FUNCTIONS.Train_Zealot_quick("now", gateway.tag)
        return actions.RAW_FUNCTIONS.no_op()

    def train_stalker(self, obs):

        completed_gateways = self.get_my_completed_units_by_type(obs, units.Protoss.Gateway)
        core_completed = True if len(self.get_my_completed_units_by_type(obs, units.Protoss.CyberneticsCore)) > 0 else False
        free_supply = obs.observation.player.food_cap - obs.observation.player.food_used
        if len(completed_gateways) > 0 and core_completed and obs.observation.player.minerals >= 125 and free_supply > 2 and obs.observation.player.vespene >= 50:
            gateway = self.get_my_units_by_type(obs, units.Protoss.Gateway)[0]
            if gateway.order_length < 5:
                return actions.RAW_FUNCTIONS.Train_Stalker_quick("now", gateway.tag)
        return actions.RAW_FUNCTIONS.no_op()

    def attack(self, obs):

        stalkers = self.get_my_units_by_type(obs, units.Protoss.Stalker)
        if len(stalkers) > 0:
            attack_xy = (38, 44) if self.base_top_left else (19, 23)
            distances = self.get_distances(obs, stalkers, attack_xy)
            zealot = stalkers[np.argmax(distances)]
            x_offset = random.randint(-4, 4)
            y_offset = random.randint(-4, 4)
            return actions.RAW_FUNCTIONS.Attack_pt("now", zealot.tag,
                                                   (attack_xy[0] + x_offset, attack_xy[1] + y_offset))

        zealots = self.get_my_units_by_type(obs, units.Protoss.Zealot)
        if len(zealots) > 0:
            attack_xy = (38, 44) if self.base_top_left else (19, 23)
            distances = self.get_distances(obs, zealots, attack_xy)
            zealot = zealots[np.argmax(distances)]
            x_offset = random.randint(-4, 4)
            y_offset = random.randint(-4, 4)
            return actions.RAW_FUNCTIONS.Attack_pt("now", zealot.tag,
                                                   (attack_xy[0] + x_offset, attack_xy[1] + y_offset))
        return actions.RAW_FUNCTIONS.no_op()


class rlAgent(ProtossAgent):

    def __init__(self):
        super(rlAgent, self).__init__()
        self.q_table = QLearningTable(self.actions)
        self.new_game()

    def step(self,obs):
        super(rlAgent, self).step(obs)
        state = str(self.get_state(obs))
        action = self.q_table.choose_action(state)
        if self.previous_action is not None:
            self.q_table.learn(self.previous_state, self.previous_action,
                               obs.reward, 'terminal' if obs.last() else state)

        self.previous_state = state
        self.previous_action = action
        return getattr(self,action)(obs)

    def new_game(self):
        self.base_top_left = None
        self.previous_state = None
        self.previous_action = None

    def reset(self):
        super(rlAgent, self).reset()
        self.new_game()


    def get_state(self, obs):

        probes = self.get_my_units_by_type(obs, units.Protoss.Probe)
        idle_probes = [probe for probe in probes if probe.order_length == 0]
        nexuses = self.get_my_units_by_type(obs, units.Protoss.Nexus)

        pylons = self.get_my_units_by_type(obs, units.Protoss.Pylon)
        completed_pylons = self.get_my_completed_units_by_type(obs, units.Protoss.Pylon)

        gateways = self.get_my_units_by_type(obs, units.Protoss.Gateway)
        completed_gateways = self.get_my_completed_units_by_type(obs, units.Protoss.Gateway)

        zealots = self.get_my_units_by_type(obs, units.Protoss.Zealot)
        queued_zealots = (completed_gateways[0].order_length if len(completed_gateways) > 0 else 0)
        free_supply = (obs.observation.player.food_cap - obs.observation.player.food_used)

        can_afford_pylon_or_zealot = obs.observation.player.minerals >= 100
        can_afford_gateway = obs.observation.player.minerals >= 150

        enemy_probes = self.get_enemy_units_by_type(obs, units.Protoss.Probe)
        enemy_nexuses = self.get_enemy_units_by_type(obs, units.Protoss.Nexus)

        enemy_pylons = self.get_enemy_units_by_type(obs, units.Protoss.Pylon)
        enemy_completed_pylons = self.get_enemy_completed_units_by_type(obs, units.Protoss.Pylon)

        enemy_gateways = self.get_enemy_units_by_type(obs, units.Protoss.Gateway)
        enemy_completed_gateways = self.get_enemy_completed_units_by_type(obs, units.Protoss.Gateway)

        enemy_zealots = self.get_enemy_units_by_type(obs, units.Protoss.Zealot)

        return (len(nexuses),
                len(probes),
                len(idle_probes),
                len(pylons),
                len(completed_pylons),
                len(gateways),
                len(completed_gateways),
                len(zealots),
                queued_zealots,
                free_supply,
                can_afford_pylon_or_zealot,
                can_afford_gateway,
                len(enemy_nexuses),
                len(enemy_probes),
                len(enemy_pylons),
                len(enemy_completed_pylons),
                len(enemy_gateways),
                len(enemy_completed_gateways),
                len(enemy_zealots))







class RandomAgent(ProtossAgent):

    def step(self, obs):
        super(RandomAgent, self).step(obs)
        action = random.choice(self.actions)
        return getattr(self, action)(obs)









def main(unused_argv):
    # agent = rlAgent()
    # agent1 = rlAgent()
    agent2 = RandomAgent()
    try:
        while True:
            with sc2_env.SC2Env(
                    map_name="Simple64",
                    players=[sc2_env.Agent(sc2_env.Race.protoss),
                             sc2_env.Bot(sc2_env.Race.protoss,
                                         sc2_env.Difficulty.very_easy)],
                    # players=[sc2_env.Agent(sc2_env.Race.protoss),
                    #          sc2_env.Agent(sc2_env.Race.protoss)],
                    agent_interface_format=features.AgentInterfaceFormat(
                        action_space=actions.ActionSpace.RAW,
                        use_raw_units=True,
                        raw_resolution=64,
                        # feature_dimensions=features.Dimensions(screen=84, minimap=64)
                    ),
            step_mul= 48,
            disable_fog=True
            ) as env:
                run_loop.run_loop([agent2], env, max_episodes=1000)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    app.run(main)