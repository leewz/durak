#!/usr/bin/env python3
# durak.py
# !Ported to GitHub.


'''
    Just keep it simple:
        - Command line.
        - Ask each player what to do.
        - No passing.

    [??:??] (two hours ago?) Start
    [2:47] Debugging phase.
    [4:16] Yayy it's done.
'''

import random
from itertools import chain, cycle
from contextlib import contextmanager
flatten = chain.from_iterable


NDEBUG = False

def main():
    player_names = ['HELLO', 'WORLD', 'GUIDO', 'VON', 'ROSSUM']
    game = Durak(player_names)
    run_game(game)


def run_game(game):
    ui = DurakUI(IO())
    ui.info("Players:")
    for i, player in enumerate(game.players):
        ui.info("%d. %s" % (i+1, player))
    ui.info("Trump is %r." % game.trump)
    ui.info()
    
    round_number = 1
    while not game.ended():
        ui.info("== Round %d ==\n" % round_number)
        run_battle(game, ui)
        ui.info("-- Round over --")
        end_round(game, ui)
        ui.info()
        round_number += 1
    ui.info("GAME OVER")
    players = list(game.players)
    if not players:
        ui.info("Everybody's out.")
    else:
        assert len(players) == 1, "There should only be one player left!"
        durak, = players
        ui.info(durak.name, "is the durak, with", len(durak.hand), "in hand.")


def run_battle(game, ui):
    """
    
        Returns whether or not the attack was successful.
    """
    table = game.table
    players = game.players
    trump = game.trump
    
    attacker = players.pop()
    defender = players.first
    attackers = tuple(players.rest)[::-1]
    assert attacker != defender
    assert attacker == attackers[0]
    assert defender not in attackers

    skipped = 0 #number of consecutive attackers skipping their attack.
    iatkrs = cycle(attackers)
    while not table.full and defender.hand and skipped < len(attackers):
        attacker = next(iatkrs)
        if not attacker.hand:
            ui.info("%r can't attack." % attacker)
            skipped += 1
            continue
        attack = ui.attack(attacker, defender, table.faces)
        if not attack:
            ui.info("%r passes." % attacker)
            skipped += 1
            continue
        ui.info("%r attacks with %r." % (attacker, attack))
        skipped = 0
        defense = table[attack] = ui.defend(defender, attack, trump)
        if not defense:
            ui.info("%r doesn't defend.\n" % defender)
            return False
        else:
            ui.info("%r defends against %r with %r.\n" % (defender, attack, defense))
    return True


def end_round(game, ui):
    table = game.table
    players = game.players
    defender = game.players.first
    attackers = game.players.rest
    
    #- Defender picks up cards, maybe.
    defended = not table.openattacks
    if not defended:
        cards = set(table.cards)
        ui.info("%r picks up %d card%s from the table."
                # % (defender, len(cards), "s" if len(cards) != 1 else ""))
                % (defender, len(cards), "s"*(len(cards) != 1))
        defender.pickup(table.cards)
    else:
        ui.info("%r successfully defended against %d attacks."
                % (defender, len(table.keys())))
    table.clear()
    
    #- Draw phase.
    deck = game.deck
    if deck:
        for player in (*attackers, defender):
        #?for player in (*reversed(attackers), defender):
            ct = drawup(player, deck)
            if ct:
                ui.info(repr(player), "draws", ct, "cards." if ct != 1 else "card.")
            if not deck:
                ui.info("Deck is empty.")
                break

    removed = players.compact() #remove empty-handed players.
    for player in removed:
        ui.info(player.name, "is out of cards.")
    
    if not defended:
        players.pop() #defender doesn't get to be next attacker.
        ui.info("Skipping", defender.name, "'s attack.")


def drawup(player, deck):
    """ draw up to 6. """
    todraw = 6 - len(player.hand)
    if todraw <= 0:
        return
    cards = deck.drawupto(todraw)
    player.pickup(cards)
    return len(cards)


def beats(defense, attack, trump):
    if defense.suit == attack.suit:
        # return defense.face > attack.face
        i = FACES.index
        return i(defense.face) > i(attack.face)
    else:
        return defense.suit == trump.suit



SUITS = 'SHCD'
FACES = '23456789TJQKA'
class Durak:
    def __init__(self, player_names):
        self.players = PlayerList(player_names)
        if len(self.players) < 6:
            self.deck = Deck(SUITS, FACES[4:])
        else:
            self.deck = Deck(SUITS, FACES)

        #- Deal initial cards.
        draw = self.deck.draw
        for i in range(6):
            for player in self.players:
                player.take(draw())
        
        # self.trump = draw()
        self.trump = self.deck.bottom
        self.table = Table()
    
    def ended(self):
        """ Whether the game's over.
        """
        players_with_cards = [player for player in self.players if len(player.hand)]
        return len(players_with_cards) <= 1



class PlayerList:
    def __init__(self, names):
        self.lst = list(map(Player, names))
        self.i = 0
    
    def pop(self):
        """ Returns next player and rotate the iterator.
            
            Used to get the attack initiator.
        """
        lst = self.lst
        i = self.i
        player = lst[i]
        assert player.hand
        self.i = (i+1) % len(lst)
        return player
    
    @property
    def first(self):
        """ 
        
            Used to get the defender.
        """
        return self.lst[self.i]
    
    @property
    def rest(self):
        """
            
            Used to get the attackers.
        """
        lst = self.lst
        i = self.i
        return lst[i+1:] + lst[:i]  #concatenate backwards
        
    def __len__(self):
        return len(self.lst)
    def __iter__(self):
        yield from self.lst

    def compact(self):
        #- Remove empty-handed players while preserving position.
        lst = self.lst
        i = self.i
        isout = lambda player: not player.hand
        fronts = ilen(filter(isout, lst[:i])) #number of players before `i`.
        self.lst, removed = map(list, partition(isout, lst))
        self.i = fronts % len(self.lst)
        return removed


class Player:
    def __init__(self, name):
        self.name = name
        self.hand = set()
    def take(self, card):
        self.hand.add(card)
    def pickup(self, cards):
        self.hand.update(cards)
    def __str__(self):
        return self.name
    def __repr__(self):
        return "%s (%d cards)" % (self.name, len(self.hand))


class Deck:
    def __init__(self, suits, faces):
        self.cards = shuffled(PlayingCard(s, f) for s in SUITS for f in FACES)
        
    def draw(self):
        return self.cards.pop()
    
    def drawupto(self, n):
        """ Draw up to the specified amount.
        """
        cards = self.cards
        drawn = cards[-n:]
        cards[-n:] = []
        return drawn
    
    def __len__(self):
        return len(self.cards)
    
    @property
    def bottom(self):
        return self.cards[0]


# from collections import namedtuple
# PlayingCard = namedtuple('PlayingCard', ['suit', 'face'])
class PlayingCard:
    def __init__(self, suit, face):
        self.suit = suit
        self.face = face
    def __str__(self):
        # return '\u2660'
        return self.face + self.suit

    def __repr__(self):
        return self.face + self.suit


class Table:
    def __init__(self):
        self.dict = {}
    @property
    def cards(self):
        return set(self.itercards())
    def itercards(self):
        for k,v in self.dict.items():
            yield k
            if v:
                yield v
    @property
    def open(self):
        "If this table has an open attack."
        return None in self.dict.values()
    @property
    def full(self):
        return len(self.dict) >= 6
    @property
    def faces(self):
        return set(card.face for card in self.itercards())


class Table(dict):
    @property
    def cards(self):
        return set(self.itercards())
    def itercards(self):
        for k,v in self.items():
            yield k
            if v:
                yield v
    @property
    def openattacks(self):
        return {attack for attack, defense in self.items() if defense is None}
    @property
    def full(self):
        return len(self) >= 6
    @property
    def faces(self):
        return set(card.face for card in self.itercards())


class DurakUI:
    def __init__(self, io):
        self.io = io
    
    def playcard(self, player, message="Choose a card", **kwargs):
        """Get the player to select a card.
        """
        with self.io.withcommands(
            hand=lambda: print("Hand:", *player.hand),
        ):
            card = self.io.choice(
                    options=player.hand,
                    # message=player.name + ", " + message + ":",
                    message=repr(player) + ", " + message + ":", #!
                    **kwargs
                )
        if card:
            player.hand.remove(card)
        return card
        
    def attack(self, attacker, defender, faces):
        return self.playcard(
                attacker,
                message="attack %r" % defender,
                validate=(lambda card: card.face in faces) if faces else None,
                optional=len(faces) > 0,
            )
    
    def defend(self, defender, attack, trump):
        return self.playcard(
                defender,
                message="defend against %r" % attack,
                validate=lambda defense: beats(defense, attack, trump),
                optional=True,
            )
    
    def event(self, event, *TODO):
        """ Inform about an event.
        """
    
    def playeract(self, player, action, *TODO):
        """ Inform about a player action.
        """
    
    def info(self, *args):
        """ General info.
        """
        print(*args)


class IO:
    commands = {}
    def choice(self, options, message="Select an option from below:", optional=False, validate=None):
        options = tuple(filter(validate, options))
            #^ Later, we might cross out invalid options.
        if optional:
            options = (*options, None)
        if not options:
            raise Exception("No valid choice!")
        print(message)
        for i,x in enumerate(options):
            print('%d. %s' % (i+1, x))
        if len(options) == 1: #No need to choose.
            print(1) #Pretend choice was made.
            return options[0]
        if not NDEBUG: #!TESTING
            i = random.randrange(len(options))
            print(i)
            return options[i]
        
        i = self.get(
                process=lambda line: int(line)-1,
                validate=lambda i: i in range(len(options)),
                errmsg="Invalid choice.",
            )
        return options[i]
    
    def get(self,
            process=None,
            validate=None,
            errmsg=None,
    ):
        while True:
            line = input()
            if line in self.commands:
                self.commands[line]()
                continue
            val = line
            if process:
                try:
                    val = process(val)
                except ValueError:
                    print(errmsg)
                    continue
            if not validate or validate(val):
                return val
            else:
                print(errmsg)
    
    def withcommands(self, **cmds):
        """Set commands temporarily.
            
        """
        return tempupdate(self.commands, cmds)


@contextmanager
def tempupdate(d0, d1):
    """ Temporarily updates dict d0 with dict d1.
    """
    olds = {}
    for k, v in d1.items():
        if k in d0:
            olds[k] = d0[k]
        d0[k] = v
    try:
        yield
    finally:
        for k, v in d1.items():
            if d0.get(k) is not v:
                continue #or raise an error?
            if k in olds:
                d0[k] = olds[k]
            else:
                del d0[k]


def shuffled(iterable):
    lst = list(iterable)
    random.shuffle(lst)
    return lst


def ilen(iterable):
    """ Length of an iterable.
    """
    return sum(1 for _ in iterable)

def partition(predicate, iterable):
    fails = []
    passes = []
    lsts = (fails, passes)
    for x in iterable:
        lsts[predicate(x)].append(x)
    return lsts



if __name__ == '__main__':
    main()

