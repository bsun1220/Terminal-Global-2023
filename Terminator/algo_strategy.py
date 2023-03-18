import gamelib
import random
import math
import warnings
from sys import maxsize
import json

class AlgoStrategy(gamelib.AlgoCore):

    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)

    def on_game_start(self, config):
 
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, IGNORE, EDGE
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        IGNORE = []
        EDGE = True
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        # Comment or remove this line to enable warnings.
        game_state.suppress_warnings(True)

        self.begin_plan(game_state)
        self.construct_backup(game_state)

        game_state.submit_turn()


    def find_result(self, turr):
        ret_val = 1
        for val in turr:
            if val[1] == 14:
                return ret_val

        ret_val += 1
        for val in turr:
            if val[1] == 15:
                return ret_val

        ret_val += 1
        for val in turr:
            if val[1] == 16:
                return ret_val
        return -1

    def trigger_turr(self, game_state):
        var = 3
        middle = [2, 15]

        locations = list(filter(lambda x: game_state.game_map.in_arena_bounds(
            x), game_state.game_map.get_locations_in_range(middle, var)))
        turr = []

        for loc in locations:
            res = game_state.game_map[loc]
            if len(res) == 0: 
                continue

            if res[0].unit_type == "DF":
                turr.append(loc)
        
        return self.find_result(turr)


    def begin_plan(self, game_state):
        defend_locations = [[5, 8]]

        if game_state.turn_number == 5:
            if self.trigger_turr(game_state) not in [-1, 2, 3]:
                EDGE = False

        self.attack_form(game_state)
        self.main_defense_form(game_state)

        if self.check(game_state):
            IGNORE.append([6, 10])
            game_state.attempt_remove(IGNORE)
        elif [6, 10] in IGNORE:
            IGNORE.remove([6, 10])
        self.defense_form(game_state)
        if game_state.turn_number >= 11 and self.dying(game_state):
            self.stop_self_harm(game_state)
        elif game_state.turn_number >= 9.9 and len(self.hold_line(game_state)) == 0:
            number_enemy_support = self.scan_enemy_for_units(game_state, "EF")
            divisor = max(9 - number_enemy_support, 5)
            game_state.attempt_spawn(INTERCEPTOR, defend_locations[0], int(
                game_state.get_resource(MP, 1) / divisor))

        if not self.dead(game_state):
            self.attack(game_state)

        self.side_defense_form(game_state)
        self.holy(game_state, self.hold_line(game_state))

    def attack(self, game_state):
        attack_location = [14, 0]
        defend_location = [5, 8]
        row_1_spawn = [1, 12]
        row_2_spawn = [2, 11]
        closest_enemy_turret_row = self.trigger_turr(game_state)

        if self.damage_spawn_location(game_state, attack_location) == 0 and game_state.get_resource(SP, 1) <= 5:
            self.support(game_state)
            if len(self.hold_line(game_state)) == 0:
                game_state.attempt_spawn(SCOUT, attack_location, 1000)
            else:
                self.holy(game_state, self.hold_line(game_state))
                game_state.attempt_spawn(SCOUT, attack_location, 1000)
        elif game_state.turn_number <= 9:
            if closest_enemy_turret_row == -1 or closest_enemy_turret_row == 3:
                if self.getting_good_placement(game_state):
                    game_state.attempt_spawn(
                        DEMOLISHER, self.getting_good_placement(game_state), 10)
                else:
                    game_state.attempt_spawn(DEMOLISHER, attack_location, 10)
            elif closest_enemy_turret_row == 2:
                if self.getting_good_placement(game_state):
                    game_state.attempt_spawn(DEMOLISHER, row_2_spawn, 10)
                else:
                    game_state.attempt_spawn(DEMOLISHER, attack_location, 10)
            else:
                game_state.attempt_spawn(DEMOLISHER, attack_location, 10)
        elif game_state.turn_number % 3 == 0 and game_state.turn_number <= 20:
            if not self.horizontal(game_state):
                self.vertical(game_state)
            if len(self.hold_line(game_state)) != 0:
                self.holy(game_state, self.hold_line(game_state))

            if closest_enemy_turret_row == -1 or closest_enemy_turret_row == 3:
                if self.getting_good_placement(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(DEMOLISHER, self.getting_good_placement(
                            game_state), self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(DEMOLISHER, self.getting_good_placement(
                            game_state), self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            elif closest_enemy_turret_row == 2:
                self.support_only_row_1(game_state)
                if self.getting_good_placement(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            else:
                self.support(game_state)
                if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                    game_state.attempt_spawn(
                        DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                    game_state.attempt_spawn(SCOUT, attack_location, 1000)
                else:
                    game_state.attempt_spawn(
                        DEMOLISHER, attack_location, self.demolisher_planner(game_state))
        elif game_state.turn_number % 4 == 2 and game_state.turn_number <= 31:
            if not self.horizontal(game_state):
                self.vertical(game_state)
            if len(self.hold_line(game_state)) != 0:
                self.holy(game_state, self.hold_line(game_state))
            self.support(game_state)
            if closest_enemy_turret_row == -1 or closest_enemy_turret_row == 3:
                if self.getting_good_placement(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(DEMOLISHER, self.getting_good_placement(
                            game_state), self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(DEMOLISHER, self.getting_good_placement(
                            game_state), self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            elif closest_enemy_turret_row == 2:
                if self.getting_good_placement(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            else:
                if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                    game_state.attempt_spawn(
                        DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                    game_state.attempt_spawn(SCOUT, attack_location, 1000)
                else:
                    game_state.attempt_spawn(
                        DEMOLISHER, attack_location, self.demolisher_planner(game_state))
        elif game_state.turn_number % 4 == 0:
            if not self.horizontal(game_state):
                self.vertical(game_state)
            if len(self.hold_line(game_state)) != 0:
                self.holy(game_state, self.hold_line(game_state))
            self.support(game_state)
            if self.count_support(game_state) >= 5 and game_state.get_resource(MP) >= 25:
                game_state.attempt_spawn(SCOUT, attack_location, int(
                    game_state.get_resource(MP) / 2))
                game_state.attempt_spawn(SCOUT, [14, 0], 1000)
            if closest_enemy_turret_row == -1 or closest_enemy_turret_row == 3:
                if self.getting_good_placement(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(DEMOLISHER, self.getting_good_placement(
                            game_state), self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(DEMOLISHER, self.getting_good_placement(
                            game_state), self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            elif closest_enemy_turret_row == 2:
                if self.getting_good_placement(game_state):
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, row_2_spawn, self.demolisher_planner(game_state))
                else:
                    if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                        game_state.attempt_spawn(
                            DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                        game_state.attempt_spawn(SCOUT, attack_location, 1000)
                    else:
                        game_state.attempt_spawn(
                            DEMOLISHER, attack_location, self.demolisher_planner(game_state))
            else:
                if 3 * self.demolisher_planner(game_state) < game_state.get_resource(MP):
                    game_state.attempt_spawn(
                        DEMOLISHER, defend_location, self.demolisher_planner(game_state))
                    game_state.attempt_spawn(SCOUT, attack_location, 1000)
                else:
                    game_state.attempt_spawn(
                        DEMOLISHER, attack_location, self.demolisher_planner(game_state))


    def damage_spawn_location(self, game_state, location):
        path = game_state.find_path_to_edge(location)
        damage = 0
        for path_location in path:
            damage += len(game_state.get_attackers(path_location, 0))

        return damage


    def build(self, game_state, buildings):
        for building in buildings:
            if building[1] not in IGNORE:
                game_state.attempt_spawn(building[0], building[1])

    def upgrade(self, game_state, buildings):
        for building in buildings:
            if building[2]:
                game_state.attempt_upgrade(building[1])

    def deploy(self, game_state, buildings):
        for building in buildings:
            if building[1] not in IGNORE:
                game_state.attempt_spawn(building[0], building[1])
                if building[2]:
                    game_state.attempt_upgrade(building[1])

    def refund(self, game_state, buildings):
        for building in buildings:
            game_state.attempt_remove([building[1]])

    def scan_enemy_for_units(self, game_state, unit_to_search):
        number_of_units = 0
        for y in range(14, 28):
            for x in range(2, 28):
                if game_state.game_map[x, y]:
                    if game_state.game_map[x, y][0].unit_type == unit_to_search:
                        number_of_units += 1
        return number_of_units

    def revive(self, game_state, buildings):
        need_repair = []
        for building in buildings:
            if game_state.game_map[building[1]]:
                if 2 * game_state.game_map[building[1]][0].health <= game_state.game_map[building[1]][0].max_health and game_state.game_map[building[1]][0].health not in [60, 75]:
                    need_repair.append(building)
        self.refund(game_state, need_repair)

    def attack_form(self, game_state):
        line = [[WALL, [15, 1], False],[WALL, [14, 2], False],[WALL, [13, 3], False],[WALL, [12, 4], False],[WALL, [11, 5], False],
        [WALL, [10, 6], False],[WALL, [9, 7], False],[WALL, [8, 8], False],[WALL, [7, 9], False],[WALL, [6, 10], False]]

        self.build(game_state, line)
        self.revive(game_state, line)

    def defense_form(self, game_state):
        line = [[TURRET, [25, 12], True],[WALL, [27, 13], False],[WALL, [26, 13], False],[WALL, [25, 11], False],[WALL, [24, 10], False],[WALL, [23, 9], True],
            [WALL, [22, 8], True],[WALL, [21, 7], False],[WALL, [20, 6], False],[WALL, [19, 5], False],
            [WALL, [18, 4], False],[WALL, [17, 3], False],[WALL, [16, 2], False]]

        self.build(game_state, line)
        self.deploy(game_state, line)
        self.revive(game_state, line)

    def main_defense_form(self, game_state):
        defense = [[TURRET, [3, 13], True],[WALL, [4, 13], True],[TURRET, [3, 12], True],
        [WALL, [4, 12], True],[TURRET, [6, 9], True],[WALL, [7, 9], True],[TURRET, [6, 9], True],[WALL, [2, 13], True],
        [WALL, [1, 13], False],[WALL, [0, 13], False],[WALL, [6, 10], True],[TURRET, [7, 8], True],[WALL, [8, 8], True],
        [WALL, [9, 7], True]]

        self.deploy(game_state, defense)
        self.revive(game_state, defense)

    def side_defense_form(self, game_state):
        defense = [[TURRET, [25, 12], True],[TURRET, [25, 12], True],[WALL, [25, 13], True],[WALL, [24, 12], True],
        [TURRET, [24, 11], False]]
        self.deploy(game_state, defense)
        self.revive(game_state, defense)

    def support(self, game_state):
        if EDGE and game_state.turn_number <= 31:
            self.support_only_row_1(game_state)
        else:
            support = [[SUPPORT, [1, 12], True],[SUPPORT, [2, 12], True],[SUPPORT, [3, 10], True],
            [SUPPORT, [4, 10], True],[SUPPORT, [4, 9], True],[SUPPORT, [2, 11], True],[SUPPORT, [3, 11], True]]

            self.deploy(
                game_state, support[:int(game_state.turn_number / 5)])

    def support_only_row_1(self, game_state):
        support = [[SUPPORT, [1, 12], True],[SUPPORT, [2, 12], True],[SUPPORT, [3, 10], True],[SUPPORT, [4, 10], True],
        [SUPPORT, [4, 9], True]]

        self.deploy(
            game_state, support[:game_state.turn_number // 5])

    def horizontal(self, game_state):
        x = 4
        y = 14
        df = []
        row = []
        while (len(df) < 3):
            if game_state.game_map[x, y]:
                row.append(game_state.game_map[x, y][0].unit_type)
            else:
                row.append(" ")
            if x == 14:
                y += 1
                x = 4
                df.append(row)
                row = []
            else:
                x += 1

        for i in [0, 1, 2]:
            x = 4
            y = 13
            builds = []
            attack = False
            for loc in df[i]:
                if loc == "DF":
                    y = 11 + i
                    attack = True
                    builds.append(x + 1)
                if loc == "FF" or loc == "EF":
                    if x != 4:
                        builds.append(x)
                    if i == 2:
                        attack = True
                x += 1
            if attack:
                z = 5
                for j in builds:
                    if game_state.get_resource(SP) >= j - z + 1:
                        while (z != j + 1):
                            game_state.attempt_spawn(WALL, [z, y])
                            game_state.attempt_remove([z, y])
                            z += 1
                return True
        return False

    def vertical(self, game_state):
        if game_state.game_map[3, 14]:
            if game_state.game_map[3, 14][0].unit_type == "DF":
                vert = [[WALL, [5, 12]]]
                self.build(game_state, vert)
                self.refund(game_state, vert)
                return True
        for i in [[2, 14], [3, 15]]:
            if game_state.game_map[i]:
                if game_state.game_map[i][0].unit_type == "DF":
                    vert = [[WALL, [5, 13]],[WALL, [7, 10]],[WALL, [7, 11]],[WALL, [7, 12]],[WALL, [7, 13]]]
                    self.build(game_state, vert)
                    self.refund(game_state, vert)
                    return True
        for i in [[1, 14], [2, 15], [3, 16], [4, 17]]:
            if game_state.game_map[i] and game_state.turn_number <= 32:
                if game_state.game_map[i][0].unit_type == "DF":
                    vert = [[WALL, [6, 11]],[WALL, [6, 12]]]
                    self.build(game_state, vert)
                    self.refund(game_state, vert)
                    return True
        vert = [[WALL, [6, 11]],[WALL, [6, 12]],[WALL, [6, 13]]]

        self.build(game_state, vert)
        self.refund(game_state, vert)
        return True

    def check(self, game_state):
        x = 4
        y = 14
        while (x <= y):
            if game_state.game_map[x, y]:
                if game_state.game_map[x, y][0].unit_type == "DF":
                    return True
            x += 1
        return False

    def hold_line(self, game_state):
        x = []
        line = [[25, 11],[24, 10],[23, 9],[22, 8],[21, 7],[20, 6],[19, 5],[18, 4],[17, 3],[16, 2]]

        for i in line:
            if not game_state.contains_stationary_unit(i):
                x.append(i)
        return x

    def holy(self, game_state, list):
        pref = [[21, 7],[22, 8],[20, 6],[19, 5],[18, 4],[17, 3],[16, 2] ]

        for i in pref:
            if i in list:
                number_enemy_support = self.scan_enemy_for_units(
                    game_state, "EF")
                divisor = max(8 - number_enemy_support, 3)
                game_state.attempt_spawn(INTERCEPTOR, i, int(
                    game_state.get_resource(MP, 1) / divisor))
                break

    def getting_good_placement(self, game_state):
        row_1_spawn = [1, 12]
        row_2_spawn = [2, 11]
        if self.isunable(game_state, row_1_spawn):
            return [1, 12]
        elif self.isunable(game_state, row_2_spawn):
            return [2, 11]
        return False

    def isunable(self, game_state, location):
        if location == [1, 12]:
            to_check = [[1, 12], [2, 12], [2, 11], [3, 11], [4, 11], [5, 11]]
        elif location == [2, 11]:
            to_check = [[2, 11], [3, 11], [4, 11], [5, 11]]
        return all(list(map(lambda x: game_state.contains_stationary_unit(x) is False, to_check)))

    def dead(self, game_state):
        locations = [[0, 14], [27, 14]]
        for location in locations:
            if game_state.contains_stationary_unit(location):
                if game_state.game_map[location][0].unit_type == "FF" and game_state.game_map[location][0].pending_removal:
                    reinforce = [[TURRET, [26, 12], True],[WALL, [27, 13], False],[WALL, [26, 13], False]]
                    self.deploy(game_state, reinforce)
                    return True
        return False

    def dying(self, game_state):
        locations = [[0, 14], [27, 14]]
        for location in locations:
            if not game_state.contains_stationary_unit(location) and game_state.get_resource(MP, 1) >= 6:
                reinforce = [[TURRET, [26, 12], True],[WALL, [27, 13], False],[WALL, [26, 13], False]]
                self.deploy(game_state, reinforce)
                return True
        return False

    def stop_self_harm(self, game_state):
        if game_state.get_resource(MP) >= 8.9:
            defend_location = [5, 8]
            row_2_spawn = [2, 11]
            if not self.horizontal(game_state):
                self.vertical(game_state)
            self.support(game_state)
            closest_enemy_turret_row = self.trigger_turr(
                game_state)
            if closest_enemy_turret_row in [-1, 2, 3]:
                if self.getting_good_placement(game_state):
                    game_state.attempt_spawn(DEMOLISHER, row_2_spawn, 1000)
                else:
                    game_state.attempt_spawn(DEMOLISHER, defend_location, 1000)
            else:
                game_state.attempt_spawn(DEMOLISHER, defend_location, 1000)

    def demolisher_planner(self, game_state):
        center = [7, 17]
        radius = 6
        locations = list(filter(lambda x: (game_state.game_map.in_arena_bounds(
            x) and x[0] <= 13), game_state.game_map.get_locations_in_range(center, radius)))
        turret_counts = 0
        for loc in locations:
            result_list = game_state.game_map[loc]
            if len(result_list) > 0:
                if result_list[0].unit_type == "DF":
                    turret_counts += 2
        if game_state.get_resource(SP, 1) >= 8:
            turret_counts += 1
        return turret_counts + 2

    def count_support(self, game_state):
        center = [10, 9]
        radius = 15
        locations = list(filter(lambda x: (game_state.game_map.in_arena_bounds(
            x) and x[1] <= 13), game_state.game_map.get_locations_in_range(center, radius)))
        support_count = 0
        for loc in locations:
            result_list = game_state.game_map[loc]
            if len(result_list) > 0:
                if result_list[0].unit_type == "EF":
                    support_count += 1
        return support_count
    
    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))

    def construct_backup(self, game_state):
        sp_amount = game_state.get_resource(SP, 0)
        old_sp = sp_amount
        if sp_amount is None or sp_amount < 30 or sp_amount > 1000:
            return 
        pink_filters_points = [[24, 11], [14, 9], [15, 9], [22, 9], [21, 8]]
        game_state.attempt_spawn(TURRET, pink_filters_points)
        game_state.attempt_upgrade(pink_filters_points[::2])

        sp_amount = game_state.get_resource(SP, 0)
        points = [[27, 13], [26, 13], [25,11], [24,10], [21, 7], [19, 5], [20, 6], [16, 2], [17, 3], [18, 4]]
        game_state.attempt_upgrade(points)

        if old_sp - sp_amount >= 5:
            return

        pink_filters_points = [[14, 10], [15, 10]]
        game_state.attempt_spawn(TURRET, pink_filters_points)
        game_state.attempt_upgrade(pink_filters_points)
        


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()