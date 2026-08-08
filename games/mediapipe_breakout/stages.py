# stages.py

STAGE_1 = {
    "block_size": (60, 25),
    "padding": 5,
    "offset": (50, 60),
    "layout": [
        "NNNNNNNNNN",
        "HHHHHHHHHH",
        "SSSSSSSSSS",
        "RRRRRRRRRR",
        "HHHHHHHHHH",
        "NNNNNNNNNN"
        #You can create the layout of the stage using the following characters:
        #"N": Normal block
        #"H": Hard block
        #"S": Speed up block
        #"R": Slow down block
    ],
    "block_types": {
        "N": {
            "hp": 1,
            "color": (0, 120, 255)
        },
        "H": {
            "hp": 3,
            "color": (0, 60, 200)
        },
        "S": {
            "hp": 1,
            "color": (0, 255, 0),
            "effect": "speed_up"
        },
        "R": {
            "hp": 1,
            "color": (255, 200, 0),
            "effect": "slow_down"
        }
    }
}
