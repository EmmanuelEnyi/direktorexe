# logic/pairings.py
def round_robin(players):
    """
    Given a list of player names, generate a round-robin pairing list.
    Each player will play against every other player once.
    """
    pairings = []
    num_players = len(players)
    for i in range(num_players):
        for j in range(i + 1, num_players):
            pairings.append((players[i], players[j]))
    return pairings

# Test the function by running this file directly:
if __name__ == "__main__":
    players = ["Alice", "Bob", "Charlie", "Diana"]
    pairs = round_robin(players)
    for pair in pairs:
        print(pair)
