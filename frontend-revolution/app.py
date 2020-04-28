import os
import urllib
import datetime
import uuid
from chalice import Chalice, Response
import jinja2
import boto3
from botocore.vendored import requests

app = Chalice(app_name='frontend-revolution')

def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(loader=jinja2.FileSystemLoader(path)).get_template(filename).render(context)

@app.route("/")
def index():
    template = render("chalicelib/templates/index.html", {})
    return Response(template, status_code=200, headers={
        "Content-Type": "text/html",
        "Access-Control-Allow-Origin": "*"
    })


@app.route('/new_session', methods=['GET'])
def new_session():
    template = render("chalicelib/templates/new_session.html", {})
    return Response(template, status_code=200, headers={
        "Content-Type": "text/html",
        "Access-Control-Allow-Origin": "*"
    })




# apis  
@app.route("/join_session", methods=["POST"], content_types=["application/x-www-form-urlencoded"])
def _join_session():
    """to dump data from form """
    data = urllib.parse.parse_qs(app.current_request.__dict__.get("_body"))
    data = {key:value[0] for key, value in data.items()}

    player_name = data["player_name"]
    session_id = data["session_id"]

    _create_player(player_name, session_id)

    return {'HTTPStatusCode': 200, 'message': 'success', 'session_id': session_id} # link to the game board

@app.route("/create_session", methods=["POST"], content_types=["application/x-www-form-urlencoded"])
def create_session():
    """to dump data from form """
    data = urllib.parse.parse_qs(app.current_request.__dict__.get("_body"))
    data = {key:value[0] for key, value in data.items()}

    player_name = data["player_name"]

    # create session
    session_id = _create_session()
    # create player
    _create_player(player_name, session_id)

    return {'HTTPStatusCode': 200, 'message': 'success', 'session_id': session_id} # link to the game board


# functions

def _create_session():
    record = {}
    record["session_id"] = str(uuid.uuid1())
    record["updated"] = str(datetime.datetime.now())
    record["players"] = []

    rSession = boto3.resource('dynamodb').Table("rSession")
    response = rSession.put_item(Item=record)

    return record["session_id"]

def _create_player(player_name, session_id):
    # check if session exist
    rSession = boto3.resource('dynamodb').Table("rSession")
    item = rSession.get_item(
            Key={
                'session_id': session_id,
            }
        )
    item = item.get("Item")

    if item is None:
        return {'HTTPStatusCode': 404, 'message': 'session not found, please go back and try again'}

    # Create player
    data = {
        "player_name": player_name, ## validate player name
        "player_id": str(uuid.uuid1()),
        "session_id":session_id,
    }    
    rPlayers = boto3.resource('dynamodb').Table("rPlayers")
    response = rPlayers.put_item(Item=data)

    # Update Session players
    item["players"].append(data["player_id"])
    rSession.put_item(Item=item)

    return {'HTTPStatusCode': 200, 'message': 'success'}




# Board this should really be in another file


class Board(object):
    def __init__(self, board_state = {}):
        
        # if newboard, initialise board
        if board_state == {}:
            board_state = {
                "plantation": self._create_new_location(6, 30),
                "tavern": self._create_new_location(4, 20),
                "cathedral": self._create_new_location(7, 35),
                "townhall": self._create_new_location(7, 45),
                "fortress": self._create_new_location(8, 50),
                "market": self._create_new_location(5, 25),
                "harbour": self._create_new_location(6, 40),}
        self.board_state = board_state

    def action_add_player_cube(self, player_id, location):
        # check if full
        if not self._count_cubes(location):
            return None
        # Since not full, add player cube
        current_cube_count = self.board_state[location]["player_cubes"].get(player_id, 0)
        if current_cube_count == 0:
            #initialise the player cube
            self.board_state[location]["player_cubes"][player_id] = 1
            self._update_max_slots(location)
            return False
        else:
            self.board_state[location]["player_cubes"][player_id] += 1
            self._update_max_slots(location)
            return True

    def action_remove_player_cube(self, player_id, location):
        current_cube_count = self.board_state[location]["player_cubes"].get(player_id, 0)
        if current_cube_count == 0:
            #initialise the player cube
            self.board_state[location]["player_cubes"][player_id] = 0
            self._update_max_slots(location)
            return False
        else:
            self.board_state[location]["player_cubes"][player_id] -= 1
            self._update_max_slots(location)
            return True

    def spy(self, spy_id, victim_id, location):

        # first remove victim_cube
        if not self.action_remove_player_cube(victim_id, location):
            return "spy failed because no victim cube"

        self.action_add_player_cube(spy_id, location)

    def apothecary(self, personA, locationA, personB, locationB):

        # check if cubes are present
        a_cube_count = self.board_state[locationA]["player_cubes"].get(personA, 0)
        b_cube_count = self.board_state[locationB]["player_cubes"].get(personB, 0)

        if a_cube_count == 0 or b_cube_count ==0:
            return "failed apothecary"
        self.spy(personB, personA, locationA)
        self.spy(personA, personB, locationB)

    @staticmethod
    def _create_new_location(max_slots, support):
        return {"max_slots":max_slots, "support": support, "player_cubes": {}, "free_space":max_slots}


    def _count_cubes(self, location, number = False):
        """count number of cubes in a location"""
        location = self.board_state[location]
        player_cubes = location["player_cubes"]
        total_cubes = sum(player_cubes.values())
        space_avaliable = (location["max_slots"] - total_cubes)

        if not number:
            return space_avaliable > 0
        else:
            return space_avaliable

    def _update_max_slots(self, location):
        self.board_state[location]["free_space"] = self._count_cubes(location, True)




class engine(object):

    def __init__(self, board, bids):
        self.board = board
        self.bids = {player_id: self.validate_bid(bid) for player_id, bid in bids.items()}

        self.red = [1, 1000, 0]
        self.black = [1, 0, 1000000]
        self.brown = [1, 1000, 1000000]
        self.red_black = [1, 0, 0]

        self.location_bid_value = {
            "general": self.red,
            "captain": self.red,
            "innkeeper": self.black,
            "magistrate": self.black,
            "priest": self.brown,
            "aristocrat": self.brown,
            "merchant": self.brown,
            "printer": self.brown,
            "rogue": self.red_black,
            "spy": self.black,
            "apothecary": self.red,
            "mercenary": self.red_black,
        }

        self.result = {}

    def engine(self):

        for key, value in self.location_bid_value.items():
            pass



    def check_winner(self, location):
        bid = self.bids[location]
        value = self.location_bid_value[location]

    
    @staticmethod
    def _compare_bids(bid, value):

        bid = { i: j.get("gold")*1 for i,j in bid.items()}
        return None


    @staticmethod
    def validate_bid(bid):
        if len(bid) <= 6:
            return bid
        else:
            new_bid = {}
            count = 0

            order = [
                "general",
                "captain",
                "innkeeper",
                "magistrate",
                "priest",
                "aristocrat",
                "merchant",
                "printer",
                "rogue",
                "spy",
                "apothecary",
                "mercenary",
            ]
            for i in order:
                if bid.get(i,{}) == {}:
                    continue
                new_bid[i] = bid.get(i,{})
                count += 1

                if count == 6:
                    break
            return new_bid









        self.support = {
            "general": 1,
            "captain": 1,
            "innkeeper": 3,
            "magistrate": 1,
            "priest": 6,
            "aristocrat": 5, 
            "merchant": 3,
            "printer": 10, 
            "rogue": 0,
            "spy": 0,
            "apothecary": 0,
            "mercenary": 3,}


        self.people_location_decoder = {
            "general": "fortress", 
            "captain": "harbour",
            "innkeeper": "tavern",
            "magistrate": "townhall",
            "priest": "cathedral",
            "aristocrat": "plantation",
            "merchant": "market"}
