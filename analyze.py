import matplotlib.pyplot as plt
from collections import Counter
import json

DATA = {}

def import_json_data():
    global DATA
    with open('games_log.json', 'r') as f:
        DATA = json.load(f)

def import_raw_data(raw):
    global DATA
    DATA = raw

def draw_profit():
    profit_list = []

    for _, value in DATA.items():
        data_split = value.split(':')
        game_profit = data_split[2]

        if game_profit.startswith('+'):
            game_profit = int(game_profit.replace('+', ''))
        elif game_profit.startswith('-'):
            game_profit = -int(game_profit.replace('-', ''))
        else:
            game_profit = int(game_profit)
        
        profit_list.append(game_profit)

    plt.plot(profit_list)
    plt.title("Profit Per Game")
    plt.ylabel("Profit")
    plt.xlabel(f"Games Played: {len(profit_list)}\nNet Profit: {sum(profit_list)}")
    plt.subplots_adjust(bottom=0.2)
    plt.show()

def draw_game_results():
    game_results = []

    for _, value in DATA.items():
        data_split = value.split(':')
        game_result = data_split[1]
        game_results.append(game_result)
    
    data = Counter(game_results)
    plt.pie([float(v) for v in data.values()], labels=[k for k in data], autopct=None)
    plt.title("Game Results Pie Chart")
    plt.xlabel("Note:\nWIN = Logical Win\nLOSS = Logical Loss\nBUST = Dealer Bust\nPUSH = Push, money back")
    plt.subplots_adjust(bottom=0.2)
    plt.show()

if __name__ == '__main__':
    import_json_data()
    draw_game_results()
    draw_profit()
