# cards.py — written by Partner, spec'd by you
CARD_TYPES = {
    "EXPLODING_KITTEN": 0,
    "DEFUSE":           1,
    "ATTACK":           2,
    "NOPE":             3,
    "SKIP":             4,
    "SHUFFLE":          5,
    "SEE_THE_FUTURE":   6,
    "FAVOR":            7,
    "CAT_TACO":         8,   # Cat cards for pair/triple effects
    "CAT_WATERMELON":   9,
    "CAT_POTATO":       10,
    "CAT_BEARD":        11,
    "CAT_RAINBOW":      12,
}

DECK_COUNTS = {
    "EXPLODING_KITTEN": 1,   # scales with player count later
    "DEFUSE":           6,   # 1 per player + extras
    "ATTACK":           4,
    "NOPE":             5,
    "SKIP":             5,
    "SHUFFLE":          4,
    "SEE_THE_FUTURE":   5,
    "FAVOR":            4,
    "CAT_TACO":         4,
    "CAT_WATERMELON":   4,
    "CAT_POTATO":       4,
    "CAT_BEARD":        4,
    "CAT_RAINBOW":      4,
}