import sc2
from sc2.player import Bot, Computer

class Battlebot(sc2.BotAI):

    def __init__(self):
        super(Battlebot)
        self.BattleDC =


    async def on_step(self, iteration: int):








def main():
    sc2.run_game(
        sc2.maps.get("battle_test_map"),
        [Bot(sc2.Race.Protoss, Battle()), Computer(sc2.Race.Terran, sc2.Difficulty.Hard)],
        realtime=False
    )

main()