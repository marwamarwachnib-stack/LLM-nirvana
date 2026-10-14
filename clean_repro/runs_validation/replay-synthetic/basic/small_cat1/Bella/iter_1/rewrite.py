DIC = {'A': [11, 11], 'K': [4, 4], 'Q': [3, 3], 'J': [20, 2],
       'T': [10, 10], '9': [14, 0], '8': [0, 0], '7': [0, 0]}


def card_value(card, trump):
    if card[1] == trump:
        return DIC.get(card[0])[0]
    return DIC.get(card[0])[1]


def total_points(cards, trump):
    return sum(card_value(c, trump) for c in cards)
