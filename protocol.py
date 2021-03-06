# poprotocol.py
# Pokemon Online protocol implemented in python
#
# (c) Toni Fadjukoff 2011 - 2012
# Licensed under BSD-style license.
# See LICENSE for details

import time
import socket
import struct
import codecs
import functools

def version_controlled(version):
    """
    Wraps a function for version control:
    This way we do not have to worry about reading too little if the structure has been extended.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapped(self, *args):
            structure_length = self.decode_number("H")
            j = self.i
            structure_version = self.decode_number("B")
            if version != structure_version:
                print("Warning: we have a different version ({}) of {} ({}) than server".format(version, func.__name__, strcture_version))
            res = func(self, *args)
            self.i = j+structure_length
            return res
        return wrapped
    return decorator

class PODecoder(object):

    def __init__(self, cmd):
        self.codec = codecs.lookup("utf_8")
        self.i = 0
        self.cmd = cmd

    #### DECODING METHODS

    def decode_number(self, fmt):
        # See http://docs.python.org/library/struct.html#format-characters
        # for explanations of fmt
        if fmt[0] != "!":
            fmt = "!%s" % fmt
        l = struct.calcsize(fmt)
        if len(self.cmd) >= self.i+l:
            n = struct.unpack(fmt, self.cmd[self.i:self.i+l])[0]
        else:
            n = 0
        self.i+=l
        return n

    def decode_flags(cmd):
        flags = 0
        while True:
            b = self.decode_number("B")
            flags = (flags << 8) + b
            if b % 128 == 0:
                 break
        return flags

    def decode_bool(self):
        b = self.decode_number("B")
        return b > 0

    def decode_bytes(self):
        l = self.decode_number("I")
        if l == 0xFFFFFFFF:
            b = ""
        else:
            b = self.cmd[self.i:self.i+l]
            self.i += l
        return b

    def decode_string(self):
        l = self.decode_number("I")
        if l == 0xFFFFFFFF:
            s = ""
        else:
            s = self.cmd[self.i:self.i+l]
            s = self.codec.decode(s)[0]
            self.i += l
        return s

    def decode_ProtocolVersion(self):
        version = self.decode_number("H")
        subversion = self.decode_number("H")
        return (version,subversion)

    def decode_color(self):
        color = Color()
        color.color_spec = self.decode_number("b")
        color.alpha = self.decode_number("H")
        color.red = self.decode_number("H")
        color.green = self.decode_number("H")
        color.blue = self.decode_number("H")
        color.pad = self.decode_number("H")
        return color

    def decode_pokeid(self):
        uid = pokeid()
        uid.pokenum = self.decode_number("H")
        uid.subnum = self.decode_number("B")
        return uid

    @version_controlled(0)
    def decode_PlayerInfo(self, cmd, i):
        player = PlayerInfo()
        player.id = self.decode_number("i")
        # network flags: none
        network_flags = self.decode_flags()
        # data flags: away, hasLadder
        data_flags = self.decode_flags()
        player.away = data_flags & 1 > 0
        player.hasLadder = data_flags & 2 > 0
        player.name = self.decode_string()
        player.color = self.decode_color()
        player.avatar = self.decode_number("H")
        player.info = self.decode_string()
        player.auth = self.decode_number("b")
        teamcount = self.decode_number("B")
        player.teams = []
        for k in range(teamcount):
            tier = self.decode_string()
            rating = self.decode_number("h")
            player.teams.append({'tier': tier, 'rating': rating})
        return player

    @version_controlled(0)
    def decode_TrainerInfo(self):
        trainerinfo = TrainerInfo()
        network_flags = self.decode_flags()
        hasBattleMessage = network_flags & 1 > 0
        trainerinfo.avatar = self.decode_number("H")
        trainerinfo.info = self.decode_string()
        if hasBattleMessages:
            trainerinfo.lose = self.decode_string()
            trainerinfo.win = self.decode_string()
            trainerinfo.tie = self.decode_string()
        return trainerinfo

    @version_controlled(0)
    def decode_Team(self, cmd, i):
        team = Team()
        network_flags = self.decode_flags()
        hasDefaultTier = flags & 1  > 0
        hasNumberOfPokemon = flags & 2 > 0
        if hasDefaultTier:
            team.defaultTier = self.decode_string()
        team.gen = self.decode_gen()
        pokes = self.decode_number("B") if hasNumberOfPokemon else 6
        for k in xrange(pokes):
            team.poke[k] = self.decode_PokePersonal(team.gen)
        return team

    @version_controlled(0)
    def decode_PokePersonal(self, gen=5):
        poke = PokePersonal()
        network_flags = self.decode_flags()
        hasGen = network_flags & 1 > 0
        hasNickname > network_flags & 2 > 0
        hasPokeball > network_flags & 4 > 0
        hasHappiness > network_flags & 8 > 0
        hasPPups > network_flags & 16 > 0
        hasIVs > network_flags & 32 > 0
        poke.gen = self.decode_gen() if hasGen else gen
        poke.pokeid = self.decode_pokeid()
        poke.level= self.decode_number("B")
        data_flags = self.decode_flags()
        poke.isShiny = data_flags & 1 > 0
        if hasNickname:
            poke.nickname = self.decode_string()
        if hasPokeball:
            poke.ball = self.decode_number("H")
        if poke.gen >= 2:
            poke.item = self.decode_number("H")
            if poke.gen >= 3:
                poke.ability = self.decode_number("H")
                poke.nature = self.decode_number("B")
            poke.gender = self.decode_number("B")
            if hasHappiness:
                poke.happiness = self.decode_number("B")
        if hasPPups:
            poke.ppups = self.decode_number("B")
        for k in xrange(4):
            poke.move[k], i = self.decode_number(cmd, i, "!I")
        for k in xrange(6):
            poke.dv[k] = self.decode_number("B")
        for k in xrange(6):
            poke.ev[k] = self.decode_number("B") if hasIVs else 31
        return poke

    def decode_ChallengeInfo(self):
        c = ChallengeInfo()
        c.description = self.decode_number("b")
        c.playerId = self.decode_number("i")
        c.clauses = self.decode_number("I")
        c.mode = self.decode_number("B")
        c.team = self.decode_number("B")
        c.gen = self.decode_gen()
        c.srctier = self.decode_string()
        c.desttier = self.decode_string()
        return c

    def decode_BattleConfiguration(self):
        bc = BattleConfiguration()
        network_flags = self.decode_flags()
        hasNumberOfIds = network_flags & 1 > 0
        data_flags = self.decode_flags()
        bc.isRated = data_flags & 1 > 0
        bc.gen = self.decode_gen()
        bc.mode = self.decode_number("B")
        bc.clauses = self.decode_number("I")
        numberOfIds = self.decode_number("B") if hasNumberOfIds else 2
        bc.id=[]
        for k in range(numberOfIds):
            bc.id.append(self.decode_number("i"))
        return bc

    def decode_TeamBattle(self):
        tb = TeamBattle()
        for k in xrange(6):
            tb.m_pokemons[k] = self.decode_PokeBattle()
        return tb

    @version_controlled(0)
    def decode_PokeBattle(self):
        pb = PokeBattle()
        pb.num = self.decode_pokeid()
        data_flags = self.decode_flags()
        pb.isShiny = data_flags & 1 > 0
        pb.nick = self.decode_string()
        pb.totalLifePoints = self.decode_number("H")
        pb.lifePoints = self.decode_number("H")
        pb.gender = self.decode_number("B")
        pb.level = self.decode_number("B")
        pb.item = self.decode_number("H")
        pb.ability = self.decode_number("H")
        pb.happiness = self.decode_number("B")
        for k in xrange(5):
            pb.normal_stats[k] = self.decode_number("H")
        for k in xrange(4):
            pb.move[k] = self.decode_BattleMove()
        for k in xrange(6):
            pb.evs[k] = self.decode_number("B")
        for k in xrange(6):
            pb.dvs[k] = self.decode_number("B")
        return pb

    # STILL IN OLD FORMAT
    def decode_ShallowShownTeam(self, cmd, i):
        t = ShallowShownTeam()
        for k in xrange(6):
            t.pokes[k] = self.decode_ShallowShownPoke(cmd, i)
        return t

    # STILL IN OLD FORMAT
    def decode_ShallowShownPoke(self, cmd, i):
        poke = ShallowShownPoke()
        poke.num, i = self.decode_PokeUniqueId(cmd, i)
        poke.level, i = self.decode_number(cmd, "B")
        poke.gender, i = self.decode_number(cmd, "B")
        has_item, i = self.decode_number(cmd, "B")
        self.item = has_item > 0
        return poke

    def decode_BattleMove(self):
        bm = BattleMove()
        bm.movenum = self.decode_number("H")
        bm.PPs = self.decode_number("B")
        bm.totalPPs = self.decode_number("B")
        return bm

    # STILL IN OLD FORMAT
    def decode_BattleStats(self, cmd, i):
        stats = BattleStats()
        for k in xrange(5):
            stats.stats[k], i = self.decode_number(cmd, i, "h")
        return (stats, i)

    # STILL IN OLD FORMAT
    def decode_BattleDynamicInfo(self, cmd, i):
        info = BattleDynamicInfo()
        for k in xrange(7):
            info.boosts[k], i = self.decode_number(cmd, i, "b")
        info.flags, i = self.decode_number(cmd, i, "B")
        return (info, i)

    # STILL IN OLD FORMAT
    def decode_ShallowBattlePoke(self, cmd, i):
        sbp = ShallowBattlePoke()
        sbp.num, i = self.decode_PokeUniqueId(cmd, i)
        sbp.nick, i = self.decode_string(cmd, i)
        sbp.lifePercent, i = self.decode_number(cmd, i, "B")
        sbp.fullStatus, i = self.decode_number(cmd, i, "I")
        sbp.gender, i = self.decode_number(cmd, i, "B")
        sbp.shiny, i = self.decode_bool(cmd, i)
        sbp.gender, i = self.decode_number(cmd, i, "B")
        return (sbp, i)

    def decode_List(self, decode_fun):
        num = self.decode_number("I")
        a = []
        for j in range(num):
            item = decode(self)
            a.append(item)
        return a
     
class POEncoder(object):

    def __init__(self):
        self.codec = codecs.lookup("utf_8")

    #### ENCODING METHODS

    def encode_string(self, ustr):
        bytes = self.codec.encode(ustr)[0]
        packed = struct.pack("!I", len(bytes)) + bytes
        return packed

    def encode_bytes(self, bytes):
        packed = struct.pack("!I", len(bytes)) + bytes
        return packed

    def encode_ProtocolVersion(self, version, subversion):
        return struct.pack("!HH", version, subversion)

    def encode_FullInfo(self, fullinfo):
        bytes = self.encode_TrainerTeam(fullinfo.team)
        bytes += struct.pack("B", fullinfo.ladder)
        bytes += struct.pack("B", fullinfo.showteam)
        bytes += self.encode_Color(fullinfo.nameColor)
        return bytes

    def encode_TrainerTeam(self, team):
        bytes = self.encode_string(team.nick)
        bytes += self.encode_string(team.info)
        bytes += self.encode_string(team.lose)
        bytes += self.encode_string(team.win)
        bytes += struct.pack("!H", team.avatar)
        bytes += self.encode_string(team.defaultTier)
        bytes += self.encode_Team(team.team)
        return bytes

    def encode_Team(self, team):
        bytes = struct.pack("B", team.gen)
        for k in xrange(6):
            bytes += self.encode_PokePersonal(team.poke[k])
        return bytes

    def encode_PokePersonal(self, poke):
        bytes = self.encode_PokeUniqueId(poke.uniqueid)
        bytes += self.encode_string(poke.nickname)
        bytes += struct.pack("!HHBBBBB", poke.item, poke.ability, poke.nature, poke.gender, poke.shiny, poke.happiness, poke.level)
        bytes += struct.pack("!4I", *poke.move)
        bytes += struct.pack("!6B", *poke.dv)
        bytes += struct.pack("!6B", *poke.ev)
        return bytes
        
    def encode_PlayerInfo(self, playerInfo):
        return struct.pack("!i", playerInfo.id) +\
        self.encode_string(playerInfo.name) +\
        self.encode_string(playerInfo.info) +\
        struct.pack("!bBh", playerInfo.auth,
        playerInfo.flags, playerInfo.rating) +\
        "".join(self.encode_PokeUniqueId(puid) for puid in playerInfo.pokemon) +\
        struct.pack("!H", playerInfo.avatar) +\
        self.encode_string(playerInfo.tier) +\
        self.encode_Color(playerInfo.color) +\
        struct.pack("!B", playerInfo.gen)

    def encode_PokeUniqueId(self, uid):
        return struct.pack("!HB", uid.pokenum, uid.subnum)

    def encode_Color(self, color):
        return struct.pack("!bhhhhh", color.color_spec, color.alpha, color.red, color.green, color.blue, color.pad)

    def encode_ChallengeInfo(self, info):
        return struct.pack("!biIB", info.dsc, info.opp, info.clauses, info.mode)

    def encode_BattleChoice(self, choice):
        ret = struct.pack("!BB", choice.slot, choice.type)
        if command.type == BattleChoice.SwitchType:
            ret += struct.pack("!b", choice.pokeSlot);
        elif command.type == BattleChoice.AttackType:
            ret += struct.pack("!bb", choice.attackSlot, attackTarget)
        elif command.type == BattleChoice.RearrangeType:
            ret += struct.pack("!bbbbbb", *choice.pokeIndices)
        return ret

class PORegistryClient(object):

    def stringReceived(self, string):
        decoder = PODecoder(string)
        event = decoder.decode_number("B")
        if event == NetworkEvents['Announcement']:
             ann = decoder.decode_string()
             self.onAnnouncement(ann)
        if event == NetworkEvents["PlayersList"]:
             name = decoder.decode_string()
             desc = decoder.decode_string()
             nump = decoder.decode_number("h")
             ip = decoder.decode_string()
             maxp = decoder.decode_number("h")
             port = decoder.decode_number("h")
             protected = decoder.decode_number("b")
             self.onPlayersList(name, desc, nump, ip, maxp, port, bool(protected))
        elif event == NetworkEvents["ServerListEnd"]:
             self.onServerListEnd()

    def onAnnouncement(self, ann):
        """
        Tells about global announcement
        """

    def onPlayersList(self, name, desc, nump, ip, maxp, port, protected):
        """
        Indicates that the registry sent us infornation about one server
        """

    def onServerListEnd(self):
        """
        Indicates that the server list has been sent
        """


def battleCommandParser(func):
    """ Denotes battle command. """
    assert(func.__name__.startswith("on_Battle_"))
    battleCmd = func.__name__[len("on_Battle_"):]
    ownCallback = "onBattle%s" % battleCmd
    commonCallback = "onBattleCommand"
    def onBattleCommand(self, bid, spot, bytes):
        args = func(self, bid, spot, bytes)
        if args is None:
            print "Args is none for command %s" % battleCmd
            return
        if hasattr(self, ownCallback):
            getattr(self, ownCallback)(bid, spot, *args)
        if hasattr(self, commonCallback):
            getattr(self, commonCallback)(battleCmd, bid, spot, *args)
    onBattleCommand.__name__ = battleCmd
    return onBattleCommand
        

class POClient(POEncoder):
    """
    Implements POProtocol
    """

    def stringReceived(self, cmd):
        cmd = PODecoder(cmd)
        ev = cmd.decode_number("B")
        evname = EventNames[ev] if 0 <= ev <= len(EventNames) else None
        if evname is None:
            self.on_ProtocolError(ev, cmd)
        if hasattr(self, "on_"+evname):
            getattr(self, "on_"+evname)(cmd)
        else:
            self.on_NotImplemented(ev, cmd)

    def on_NotImplemented(self, ev, cmd):
        evname = EventNames[ev]
        print "Received command:", evname
        print "Received", len(cmd.cmd), "bytes"
        print tuple(ord(i) for i in cmd.cmd)

    def on_ProtocolError(self, ev, cmd):
        print "Received unknown byte:", ev
        print "Received", len(cmd.cmd), "bytes"
        print tuple(ord(i) for i in cmd.cmd)

    #### COMMANDS TO BE SENT TO SERVER

    version = (0,0)

    def login(self, name, **kwargs):
        data =  struct.pack('B', NetworkEvents['Login'])
        data += self.encode_ProtocolVersion(*self.version)
        # hasClientType = (1 << 0)
        # hasVersionNumber = (1 << 1)
        # hasDefaultChannel = (1 << 3)
        network_flags = struct.pack("!B", (1 << 0) | (1 << 1) | (1 << 3))
        data += network_flags
        data += self.encode_string(kwargs.get('clientType', u"python"))
        data += struct.pack('!H', 0x200)
        data += self.encode_string(name)
        # wantsIdsWithMessages
        data_flags = struct.pack("!B", 16)
        data += data_flags
        data += self.encode_string(kwargs.get('defaultChannel', u"default"))
        print "Sending login packet of " + str(len(data)) + " bytes"
        whole_packet = struct.pack('!I', len(data))+data
        print "PACKET: [" + " ".join(str(ord(b)) for b in whole_packet) + "]"
        print "Sent login packet of " + str(len(data)) + " bytes"
        self.send(data)

    def sendMessage(self, message):
        tosend=struct.pack('B', NetworkEvents['SendMessage']) + self.encode_string(message)
        self.send(tosend)

    def register(self):
        tosend=struct.pack('B', NetworkEvents['Register'])
        self.send(tosend)

    def askForPass(self, u):
        tosend = struct.pack('B', NetworkEvents['AskForPass']) + self.encode_string(u)
        self.send(tosend) 

    def sendTeam(self, trainerteam):
        tosend = struct.pack('B', NetworkEvents['SendTeam']) + self.encode_TrainerTeam(trainerteam)
        self.send(tosend)

    def challengeStuff(self, challengeinfo):
        tosend = struct.pack('B', NetworkEvents['ChallengeStuff']) + self.encode_ChallengeInfo(challengeinfo)
        self.send(tosend)

    def spectateBattle(self, battleid):
        tosend = struct.pack('!Bi', NetworkEvents['SpectateBattle'], battleid)
        self.send(tosend)

    def spectatingBattleFinished(self, battleid):
        tosend = struct.pack('!Bi', NetworkEvents['SpectatingBattleFinished'], battleid)
        self.send(tosend)

    def battleCommand(self, battleid, slot, battlecommand):
        tosend = struct.pack('!BiB', NetworkEvents['BattleCommand'], battleid, slot) + self.encode_BattleChoice(battlecommand)
        self.send(tosend)

    def battleFinished(self, battleid, result):
        tosend = struct.pack('!Bii', NetworkEvents['BattleFinished'], battleid, result)
        self.send(tosend)

    def battleChat(self, battleid, message):
        tosend = struct.pack('!BI', NetworkEvents['BattleChat'], battleid) + self.encode_string(message)
        self.send(tosend)

    def spectatingBattleChat(self, battleid, message):
        tosend = struct.pack('!BI', NetworkEvents['SpectatingBattleChat'], battleid) + self.encode_string(message)
        self.send(tosend)

    def sendPM(self, playerid, message):
        tosend = struct.pack('!BI', NetworkEvents['SendPM'], playerid) + self.encode_string(message)
        self.send(tosend)

    def sendChannelMessage(self, chanid, message):
        tosend = struct.pack('!BI', NetworkEvents['ChannelMessage'], chanid) + self.encode_string(message)
        self.send(tosend)

    def joinChannel(self, channelname):
        tosend = struct.pack('B', NetworkEvents['JoinChannel']) + self.encode_string(channelname)
        self.send(tosend)

    def partChannel(self, channel):
        tosend = struct.pack('!Bi', NetworkEvents['LeaveChannel'], channel)
        self.send(tosend)

    def kick(self, player):
        tosend = struct.pack('!Bi', NetworkEvents['PlayerKick'], player)
        self.send(tosend)

    def ban(self, player):
        tosend = struct.pack('!Bi', NetworkEvents['PlayerBan'], player)
        self.send(tosend)

    def nameBan(self, name):
        tosend = struct.pack('!Bi', NetworkEvents['CPBan'], self.encode_string(name))
        self.send(tosend)

    def away(self, away):
        tosend = struct.pack('!BB', NetworkEvents['Away'], int(True if away else False))
        self.send(tosend)

    def setProxyIP(self, data):
        tosend = struct.pack('B', NetworkEvents['SetIP']) + self.encode_string(data)
        self.send(tosend)

    def send(self, data):
        data = struct.pack('!I', len(data))+data
        self.native_send(data)
        

    ### Battle Messages and their handling

    def handleBattleCommand(self, battleid, bytes):
        msgnro, i = self.decode_number(bytes, 0, "B")
        spot, i = self.decode_number(bytes, i, "B")
        name = BattleCommandNames[msgnro] if 0 <= msgnro <= len(BattleCommandNames) else None
        if name:
            if hasattr(self, "on_Battle_"+name):
                getattr(self, "on_Battle_"+name)(battleid, spot, bytes[i:])
            else:
                self.on_Battle_NotImplemented(battleid, spot, bytes)
        else:
            self.on_Battle_ProtocolError(battleid, spot, bytes)

    @battleCommandParser
    def on_Battle_NotImplemented(self, bid, spot, bytes):
        print "Not implemented Battle Protocol:"
        print tuple(ord(i) for i in bytes)
        return()

    @battleCommandParser
    def on_Battle_ProtocolError(self, bid, spot, bytes):
        print "Error in Protocol for battle=%d, event=%d, spot=%d" % (bid, bytes[0], bytes[1])
        print tuple(ord(i) for i in bytes)
        print BattleCommandNames
        return ()

    @battleCommandParser
    def on_Battle_SendOut(self, bid, spot, bytes):
        silent, i = self.decode_bool(bytes, 0)
        prevIndex, i = self.decode_number(bytes, i, "B")
        poke, i = self.decode_ShallowBattlePoke(bytes, i)
        return (silent, prevIndex, poke)

    def onBattleSendOut(self, bid, spot, silent, prevIndex, poke):
        """
        SendOut - called when a pokemon on send on the field
        bid : int - battle id
        spot : int - spot in the field
        silent : bool - should this be announced?
        prevIndex : uint8 - which was the previous index?
        """

    @battleCommandParser
    def on_Battle_SendBack(self, bid, spot, bytes):
        return ()

    def onBattleSendBack(self, bid, spot):
        """
        SendBack - called when a pokemon is called back
        bid : int - battle id
        spot : int - spot in the field
        """
    @battleCommandParser
    def on_Battle_OfferChoice(self, bid, spot, bytes):
        pass # TODO interactive stuff

    @battleCommandParser
    def on_Battle_UseAttack(self, bid, spot, bytes):
        attack, i = self.decode_number(bytes, 0, "!H")
        return (attack,)

    def onBattleUseAttack(self, bid, spot, attack):
        """
        UseAttack - called when a pokemon uses a attack
        bid : int - battle id
        spot : int - spot in the field
        attack : uint16 - the number of the used attack
        """

    @battleCommandParser
    def on_Battle_BeginTurn(self, bid, spot, bytes):
        turn, i = self.decode_number(bytes, 0, "i")
        return (turn,)

    def onBattleBeginTurn(self, bid, spot, turn):
        """
        BeginTurn - called when a new turn starts
        bid : int - battle id
        spot : int - spot in the field
        turn : uint16 - the turn which starts
        """
 
    @battleCommandParser
    def on_Battle_ChangePP(self, bid, spot, bytes):
        pass # TODO interactive stuff

    @battleCommandParser
    def on_Battle_ChangeHp(self, bid, spot, bytes):
        hp, i = self.decode_number(bytes, 0, "!H") 
        return (hp,)

    def onBattleChangeHp(self, bid, spot, hp):
        """
        ChangeHp - called when HP value changes
        bid : int - battle id
        spot : int - spot in the field
        hp : uint16 - hp value for us, percentage for foe
        """

    @battleCommandParser
    def on_Battle_Ko(self, bid, spot, bytes):
        return ()

    def onBattleKo(self, bid, spot):
        """
        Ko - called when someone is KO'd
        bid : int - battle id
        spot : int - spot in the field
        """

    @battleCommandParser
    def on_Battle_Effective(self, bid, spot, bytes):
        eff, i = self.decode_number(bytes, 0, "B")
        return (eff,)

    def onBattleEffective(self, bid, spot, eff):
        """
        Effective - called when a move is not very or super effective
        bid : int - battle id
        spot : int - spot in the field
        eff : byte - the effectiveness of the move
        """

    @battleCommandParser
    def on_Battle_Miss(self, bid, spot, bytes):
        return ()

    def onBattleMiss(self, bid, spot):
        """
        Miss - called when a miss occurs
        bid : int - battle id
        spot : int - spot in the field
        """

    @battleCommandParser
    def on_Battle_CriticalHit(self, bid, spot, bytes):
        return ()

    def onBattleCriticalHit(self, bid, spot):
        """
        CriticalHit - called when a critical hit occurs
        bid : int - battle id
        spot : int - spot in the field
        """

    @battleCommandParser
    def on_Battle_Hit(self, bid, spot, bytes):
        return ()

    def onBattleHit(self, bid, spot):
        """
        Hit - called when a hit occurs
        bid : int - battle id 
        spot : int - spot in the field
        """

    @battleCommandParser
    def on_Battle_StatChange(self, bid, spot, bytes):
        stat, i = self.decode_number(bytes, 0, "b")
        boost, i = self.decode_number(bytes, i, "b")
        return (stat, boost)

    def onBattleStatChange(self, bid, spot, stat, boost):
        """
        StatChange - a stat changes
        bid : int - battle id
        spot : int - spot in the field
        stat : int8 - the stat affected
        boost : int8 - the boost in the stat
        """

    @battleCommandParser
    def on_Battle_StatusChange(self, bid, spot, bytes):
        status, i = self.decode_number(bytes, 0, "b")
        multiturn, i = self.decode_number(bytes, i, "B")
        return (status, multiturn > 0)

    def onBattleStatusChange(self, bid, spot, status, multiturn):
        """
        StatusChange - status changes
        bid : int - battle id
        spot : int - spot in the field
        status : int8 - status number
        multiturn : bool - not used
        """

    @battleCommandParser
    def on_Battle_StatusMessage(self, bid, spot, bytes):
        statusmessage, i = self.decode_number(bytes, 0, "b")

        # StatusFeeling
        statusmessage = {
            0: "FeelConfusion",
            1: "HurtConfusion",
            2: "FreeConfusion",
            3: "PrevParalysed",
            4: "PrevFrozen",
            5: "FreeFrozen",
            6: "FeelAsleep",
            7: "FreeAsleep",
            8: "HurtBurn",
            9: "HurtPoison"
        }.get(statusmessage, "Unknown")
 
        return (statusmessage,)

    def onBattleStatusMessage(self, bid, spot, statusmessage):
        """
        StatusMessage - a new status related message
        statusmessage : int8 - the id of the status message
        """

    @battleCommandParser
    def on_Battle_Failed(self, bid, spot, bytes):
        silent, i = self.decode_bool(bytes, 0)
        return (silent,)

    def onBattleFailed(self, bid, spot, silent):
        """
        Failed - a move failed
        silent : bool - a silent failure
        """

    @battleCommandParser
    def on_Battle_BattleChat(self, bid, spot, bytes):
        message, i = self.decode_string(bytes, 0)
        return (message,)

    def onBattleBattleChat(self, bid, spot, message):
        """
        BattleChat - a player chats
        message : string - the message including player name
        """

    @battleCommandParser
    def on_Battle_MoveMessage(self, bid, spot, bytes):
        move, i = self.decode_number(bytes, 0, "!H")
        part, i = self.decode_number(bytes, i, "B")
        type, i = self.decode_number(bytes, i, "b")
        foe, i = self.decode_number(bytes, i, "b")
        other, i = self.decode_number(bytes, i, "!h")
        q, i = self.decode_string(bytes, i)
        return (move, part, type, foe, other, q)

    def onBattleMoveMessage(self, bid, spot, move, part, type, foe, other, q):
        """
        MoveMessage - a move related message
        move : uint16 - the move id
        part : uint8 - the sub id of the message
        type : int8 - the elemental type of the message
        foe : int8 - foe spot
        other : int16 - additional numeric information
        q : string - additional string information
        """

    @battleCommandParser
    def on_Battle_ItemMessage(self, bid, spot, bytes):
        item, i = self.decode_number(bytes, 0, "!H")
        part, i = self.decode_number(bytes, i, "B")
        foe, i = self.decode_number(bytes, i, "b")
        berry, i = self.decode_number(bytes, i, "!H")
        other, i = self.decode_number(bytes, i, "!H")
        return (item, part, foe, berry, other)

    def onBattleItemMessage(self, bid, spot, item, part, foe, berry, other):
        """
        ItemMessage - an item related message
        """

    @battleCommandParser
    def on_Battle_NoOpponent(self, bid, spot, bytes):
        return ()

    def onBattleNoOpponent(self, bid, spot):
        """
        NoOpponent - there's no opponent message
        """

    @battleCommandParser
    def on_Battle_Flinch(self, bid, spot, bytes):
        return ()

    def onBattleFlinch(self, bid, spot):
        """
        Flinch - flinch happened message
        """

    @battleCommandParser
    def on_Battle_Recoil(self, bid, spot, bytes):
        damage, i = self.decode_number(bytes, 0, "B")
        return (damage,)

    def onBattleRecoil(self, bid, spot, damage):
        """
        Recoil - a recoil or draining happened
        """

    @battleCommandParser
    def on_Battle_WeatherMessage(self, bid, spot, bytes):
        wstatus, i = self.decode_number(bytes, 0, "B")
        weather, i = self.decode_number(bytes, i, "B")

        # WeatherM
        wstatus = {
           0: "ContinueWeather",
           1: "EndWeather",
           2: "HurtWeather",
        }.get(wstatus, "Unknown")

        # Weather
        weather = {
           0: "NormalWeather",
           1: "Hail",
           2: "Rain",
           3: "SandStorm",
           4: "Sunny"
        }

        return (wstatus, weather)

    def onBattleWeatherMessage(self, bid, spot, wstatus, weather):
        """
        WeatherMessage
        """

    @battleCommandParser
    def on_Battle_StraightDamage(self, bid, spot, bytes):
        damage, i = self.decode_number(bytes, 0, "!H")
        return (damage,)

    def onBattleStraightDamage(self, bid, spot, damage):
        """
        StraightDamage
        """

    @battleCommandParser
    def on_Battle_AbilityMessage(self, bid, spot, bytes):
        ab, i = self.decode_number(bytes, 0, "!H")
        part, i = self.decode_number(bytes, i, "B")
        type, i = self.decode_number(bytes, i, "b")
        foe, i = self.decode_number(bytes, i, "b")
        other, i = self.decode_number(bytes, i, "!h")
        return (ab, part, type, foe, other)

    def onBattleAbilityMessage(self, bid, spot, ab, part, type, foe, other):
        """
        AbilityMessage
        """

    @battleCommandParser
    def on_Battle_AbsStatusChange(self, bid, spot, bytes):
        poke, i = self.decode_number(bytes, 0, "b")
        status, i = self.decode_number(bytes, i, "b")
        return (poke, status)

    def onBattleAbsStatusChange(self, bid, spot, poke, status):
        """
        AbsStatusChange
        """

    @battleCommandParser
    def on_Battle_Substitute(self, bid, spot, bytes):
        is_sub, i = self.decode_number(bytes, 0, "b")
        return (is_sub > 0,)

    @battleCommandParser
    def on_Battle_BattleEnd(self, bid, spot, bytes):
        res, i = self.decode_number(bytes, 0, "b")
        return (BattleResult[res],)

    @battleCommandParser
    def on_Battle_BlankMessage(self, bid, spot, bytes):
        return ()

    @battleCommandParser
    def on_Battle_CancelMove(self, bid, spot, bytes):
        return ()

    @battleCommandParser
    def on_Battle_Clause (self, bid, spot, bytes):
        return ()

    @battleCommandParser
    def on_Battle_DynamicInfo (self, bid, spot, bytes):
        info, i = self.decode_BattleDynamicInfo(bytes, 0)
        return (info,)

    @battleCommandParser
    def on_Battle_DynamicStats (self, bid, spot, bytes):
        stats, i = self.decode_BattleStats(bytes, 0)
        return (stats,)

    @battleCommandParser
    def on_Battle_Spectating(self, bid, spot, bytes):
        come, i = self.decode_number(bytes, 0, "b")
        player, i = self.decode_number(bytes, i, "!i")
        try:
            name, i = self.decode_string(bytes, i)
        except:
            name = None
        return (come > 0, player, name)

    @battleCommandParser
    def on_Battle_SpectatorChat(self, bid, spot, bytes):
        player, i = self.decode_number(bytes, 0, "!i")
        message, i = self.decode_string(bytes, i)
        return (player, message)

    @battleCommandParser
    def on_Battle_AlreadyStatusMessage(self, bid, spot, bytes):
        status, i = self.decode_number(bytes, 0, "B")
        return (status,)

    @battleCommandParser
    def on_Battle_TempPokeChange(self, bid, spot, bytes):
        type, i = self.decode_number(bytes, 0, "B")
        if type in (TempPokeChange['TempMove'], TempPokeChange['DefMove']):
            slot, i = self.decode_number(bytes, i, "!b")
            move, i = self.decode_number(bytes, i, "!h")
            return ("MoveChange", slot, move, type == TempPokeChange['DefMove'])
        elif type in (TempPokeChange['TempPP'],):
            slot, i = self.decode_number(bytes, i, "!B")
            pp, i = self.decode_number(bytes, i, "!B")
            return ("TempPPChange", slot, pp)
        elif type in (TempPokeChange['TempSprite'],):
            temp_sprite, i = self.decode_PokeUniqueId(bytes, i)
            if temp_sprite.pokenum == -1:
                return ("PokemonVanish",)
            elif temp_sprite == 0:
                return ("PokemonReappear",)
            else:
                return ("SpriteChange", temp_sprite)
            
        elif type in (TempPokeChange['DefiniteForme'],):
            poke, i = self.decode_number(bytes, i, "!B")
            poke_id, i = self.decode_PokeUniqueId(bytes, i)
            return ("DefiniteFormeChange", poke, poke_id)
        elif type in (TempPokeChange['AestheticForme'],):
            newforme, i = self.decode_number(bytes, i, "!H")
            return ("CosmeticFormeChange", newforme)

    @battleCommandParser
    def on_Battle_ClockStart (self, bid, spot, bytes):
        clock, i = self.decode_number(bytes, 0, "!H")
        return (clock,)

    @battleCommandParser
    def on_Battle_ClockStop (self, bid, spot, bytes):
        clock, i = self.decode_number(bytes, 0, "!H")
        return (clock,)

    @battleCommandParser
    def on_Battle_Rated(self, bid, spot, bytes):
        rated, i = self.decode_number(bytes, 0, "!B")
        return (rated,)

    @battleCommandParser
    def on_Battle_TierSection (self, bid, spot, bytes):
        tier, i = self.decode_string(bytes, 0)
        return (tier,)

    @battleCommandParser
    def on_Battle_EndMessage(self, bid, spot, bytes):
        message, i = self.decode_string(bytes, 0)
        return (message,)

    @battleCommandParser
    def on_Battle_PointEstimate(self, bid, spot, bytes):
        first, i = self.decode_number(bytes, 0, "!B")
        second, i = self.decode_number(bytes, i, "!B")
        return (first, second)

    @battleCommandParser
    def on_Battle_MakeYourChoice(self, bid, spot, bytes):
        return ()

    @battleCommandParser
    def on_Battle_Avoid(self, bid, spot, bytes):
        return ()

    @battleCommandParser
    def on_Battle_RearrangeTeam(self, bid, spot, bytes):
        t, i = self.decode_ShallowShownTeam(bytes, 0)
        return (t,)

    @battleCommandParser
    def on_Battle_SpotShifts(self, bid, spot, bytes):
        s1, i = self.decode_number(bytes, 0, "!B")
        s2, i = self.decode_number(bytes, i, "!B")
        silent, i = self.decode_number(bytes, i, "!B")
        return (s1, s2, silent > 0)

    def onBattleCommand(self, command, bid, spot, *args):
        """
        The catch-all of battle commands.
        """

    ### Events from connecting to server

    def on_VersionControl(self, cmd):
        current_version = cmd.decode_ProtocolVersion()
        hasZip = cmd.decode_number("B")
        new_version = self.decode_ProtocolVersion()
        compactability_version = self.decode_ProtocolVersion()
        major_compactability_version = cmd.decode_ProtocolVersion()
        name = cmd.decode_string()
        # Really, ignore all the useless stuff it isn't needed by clients
        if self.version < compactability_version:
            print "VersionControl: EXCEPT PROBLEMS"
        if self.version < major_compactability_version:
            print "VersionControl: EXCEPT MAJOR PROBLEMS"
        self.onVersionControl(current_version, name)

    def onVersionControl(self, version, name):
        """
        Event launched soon after connection is made
        version : tuple - the server version
        name : unicode - the name of server
        """

    def on_Register(self, cmd):
        self.onRegister()

    def onRegister(self):
        """
        Event telling us that we can register our name
        """

    def on_AskForPass(self, cmd):
        salt = cmd.decode_string()
        self.onAskForPass(salt)

    def on_Login(self, cmd):
        hasReconnect = cmd.decode_number("B")
        if hasReconnect > 0:
            reconnectPass = cmd.decode_bytes()
        player = cmd.decode_PlayerInfo()
        tiers = cmd.decode_List(cmd.decode_string)
        self.onLogin(player)

    def onLogin(self, playerInfo):
        """
        Event telling us that player has logged into server
        playerInfo : PlayerInfo - contains the data of the player
        """

    def on_Logout(self, cmd):
        playerid = cmd.decode_number("i")
        self.onLogout(playerid)

    def onLogout(self, playerid):
        """
        Event telling us that a player has logged out
        playerid : int - the id of the player
        """

    def on_Announcement(self, cmd):
        announcement = cmd.decode_string()
        self.onAnnouncement(announcement)

    def onAnnouncement(self, announcement):
        """
        Event telling us that the server send an announcement
        announcement : unicode - the announcement server send
        """

    def on_KeepAlive(self, cmd):
        pass

    def on_TierSelection(self, cmd):
        tiers = {}
        stack = []
        raw, _ = self.decode_bytes(cmd, 0)
        pairs = []
        i = 0
        while i < len(raw):
            currentLevel, i = self.decode_number(raw, i, "B")
            name, i = self.decode_string(raw, i)
            pairs.append((currentLevel, name))
        self.onTierSelection(pairs)

    def onTierSelection(self, pairs):
        """
        Event telling us the Tier list of this server
        pairs : list of [int, unicode] - contains the tree structure of tiers 
        """

    def on_ChannelsList(self, cmd):
        numitems, i = self.decode_number(cmd, 0, "!I")
        channels = []
        for k in xrange(numitems):
            chanid, i = self.decode_number(cmd, i, "!i")
            channame, i = self.decode_string(cmd, i) 
            channels.append([chanid, channame])
        self.onChannelsList(channels)

    def onChannelsList(self, channels):
        """
        Event telling us the channel list of the server
        channels : list of [int, unicode] - contains channel IDs and names
        """

    def on_PlayersList(self, cmd):
        i = 0
        players = []
        while i < len(cmd):
            player, i = self.decode_PlayerInfo(cmd, i)
            players.append(player)
        self.onPlayersList(players)

    def onPlayersList(self, playerInfo):
        """
        Event containing the info of a player. Sent after log in.
        playerInfo : PlayerInfo - the info of the players, (list)
        """

    def on_PlayerBan(self, cmd):
        playerid, i = self.decode_number(cmd, 0, "!i")
        srcid, i = self.decode_number(cmd, i, "!i")
        self.onPlayerBan(playerid, srcid)

    def onPlayerBan(self, player, src):
        """
        Event telling us that someone was banned.
        player : int - the id of the player
        src : int - the id of the banner
        """

    def on_PlayerKick(self, cmd):
        playerid, i = self.decode_number(cmd, 0, "!i")
        srcid, i = self.decode_number(cmd, i, "!i")
        self.onPlayerKick(playerid, srcid)

    def onPlayerKick(self, player, src):
        """
        Event telling us that someone was kicked.
        player : int - the id of the player
        src : int - the id of the kicker
        """

    def on_BattleList(self, cmd):
        channel, i = self.decode_number(cmd, 0, "!i")
        j, i = self.decode_number(cmd, i, "!I")
        battles = {}
        for k in xrange(j):
            bid, i = self.decode_number(cmd, i, "!I")
            p1, i = self.decode_number(cmd, i, "!i")
            p2, i = self.decode_number(cmd, i, "!i")
            battles[bid] = (p1, p2)
        self.onBattleList(channel, battles)

    def onBattleList(self, channel, battles):
        """
        Event telling us all the battles
        that are happening on a channel.
        channel : int - channel to consider
        battles : hash 
           - hashing from battle id : int
             to (player1 : int, player2 : int)
        """

    def on_SpectateBattle(self, cmd):
        battleid, i = self.decode_number(cmd, 0, "!i")
        battleconf, i = self.decode_BattleConfiguration(cmd, i)
        self.onSpectateBattle(battleid, battleconf)

    def onSpectateBattle(self, battleid, battleconf):
        """
        Event telling us that we are now spectating a battle.
        battleid : int - the battle id
        battleconf : BattleConfiguration - battle conf
        """

    def on_SpectatingBattleMessage(self, cmd):
        battleid, i = self.decode_number(cmd, 0, "!i")
        b, i = self.decode_bytes(cmd, i)
        self.handleBattleCommand(battleid, b)
        self.onSpectatingBattleMessage(battleid, b)
        
    def onSpectatingBattleMessage(self, battleid, command):
        """
        Event telling us information about a battle.
        battleid : int - the battle id
        command : bytes - arbitrary battle command
        """

    def on_SpectatingBattleFinished(self, cmd):
        battleid, i = self.decode_number(cmd, 0, "!i")
        self.onSpectatingBattleFinished(battleid)

    def onSpectatingBattleFinished(self, battleid):
        """
        Event telling us that a battle has ended.
        battleid : int - the battle id
        """

    ### Pokemon related events
    def on_SendTeam(self, cmd):
        player, i = self.decode_PlayerInfo(cmd, 0)
        self.onSendTeam(player)

    def onSendTeam(self, playerInfo):
        """
        Event telling us about a team change
        playerInfo : PlayerInfo - the new info of the player
        """

    ### Battle related events

    def on_ChallengeStuff(self, cmd):
        chall, i = self.decode_ChallengeInfo(cmd, 0)
        self.onChallengeStuff(chall)

    def onChallengeStuff(self, challengeInfo):
        """
        Event telling us that we have been challenged
        challengeInfo : ChallengeInfo - the info of the challenge
        """

    def on_EngageBattle(self, cmd):
        battleid, i = self.decode_number(cmd, 0, "!i")
        pid1, i = self.decode_number(cmd, i, "!i")
        pid2, i = self.decode_number(cmd, i, "!i")
        if pid1 == 0:
            battleconf, i = self.decode_BattleConfiguration(cmd, i)
            teambattle, i = self.decode_TeamBattle(cmd, i)
            self.onEngageBattle(battleid, pid1, pid2, battleconf, teambattle)
        else:
            self.onEngageBattle(battleid, pid1, pid2, None, None)

    def onEngageBattle(self, battleid, player1, player2, battleConf, teamBattle):
        """
        Event telling us the basic info when a battle begins
        battleid : int - the id of this battle
        player1 : int - the id of player 1 - if 0, this is our battle
        player2 : int - the id of our enemy
        Following are not None only if this is our battle:
        battleConf : BattleConfiguration - the configuration of this battle
        teamBattle : TeamBattle - contains our team for this battle
        """

    def on_BattleMessage(self, cmd):
        battleid, i = self.decode_number(cmd, 0, "!i")
        b, i = self.decode_bytes(cmd, i)
        self.handleBattleCommand(battleid, b)
        self.onBattleMessage(battleid, b)

    def onBattleMessage(self, battleid, bytes):
        """
        Event telling us that Battle Message was received
        It is recommended to use onBattle* functions which will parse
        the rest of the battle message event too
        battleid : int - the id of the battle
        bytes : bytes - rest of event
        """

    def on_BattleFinished(self, cmd):
        battleid, i = self.decode_number(cmd, 0, "!i")
        result, i = self.decode_number(cmd, i, "!B")
        winner, i = self.decode_number(cmd, i, "!i")
        loser, i = self.decode_number(cmd, i, "!i")
        outcome = BattleResult[result]
        self.onBattleFinished(battleid, outcome, winner, loser)

    def onBattleFinished(self, battleid, outcome, winner, loser):
        """
        Event telling us that a battle finished
        battleid : int - the id of the battle
        outcome : str - either Forfeit, Win, Tie or Close
        winner : int - the id of the winning player
        loser : int - the id of the losing player
        """
      
    ### Channel related events

    def on_ChannelPlayers(self, cmd):
        chanid, i = self.decode_number(cmd, 0, "!i")
        numitems, i = self.decode_number(cmd, i, "!I")
        playerlist = []
        for k in xrange(numitems):
            playerid, i = self.decode_number(cmd, i, "!i")
            playerlist.append(playerid)
        self.onChannelPlayers(chanid, playerlist)
    
    def onChannelPlayers(self, chanid, playerlist):
        """
        Event telling us the players of a channel
        chanid : int - the id of the channel
        playerlist : list of ints - contains the ids of the players
        """

    def on_JoinChannel(self, cmd):
        chanid, i = self.decode_number(cmd, 0, "!i")
        playerid, i = self.decode_number(cmd, i, "!i")
        self.onJoinChannel(chanid, playerid) 

    def onJoinChannel(self, chanid, playerid):
        """
        Event telling us that a player joined a channel
        chanid : int - the id of the channel
        playerid : int - the id of the player
        """

    def on_LeaveChannel(self, cmd):
        chanid, i = self.decode_number(cmd, 0, "!i")
        playerid, i = self.decode_number(cmd, i, "!i")
        self.onLeaveChannel(chanid, playerid)

    def onLeaveChannel(self, chanid, playerid):
        """
        Event telling us that a player left a channel
        chanid : int - the id of the channel
        playerid : int - the id of the player
        """

    def on_ChannelBattle(self, cmd):
        chanid, i = self.decode_number(cmd, 0, "!i")
        battleid, i = self.decode_number(cmd, 0, "!i")
        player1, i = self.decode_number(cmd, i, "!i")
        player2, i = self.decode_number(cmd, i, "!i")
        self.onChannelBattle(chanid, battleid, player1, player2)

    def onChannelBattle(self, chanid, battleid, player1, player2):
        """
        Event telling us that a battle is underway and the
        battle should be associated with the channel
        because a player has joined the channel.
        chanid : int - the id of the channel
        battleid : int - the id of the battle
        player1 : int - the id of the first player
        player2 : int - the id of the second player
        """

    def on_ChannelMessage(self, cmd):
        chanid, i = self.decode_number(cmd, 0, "!i")
        message, i = self.decode_string(cmd, i)
        splitted = message.split(":", 1)
        if len(splitted) == 2:
            user = splitted[0]
            msg = splitted[1].lstrip()
            self.onChannelMessage(chanid, user, msg)
        else:
            self.onChannelMessage(chanid, "", message)

    def onChannelMessage(self, chanid, user, message):
        """
        Event telling us that a player messaged a channel
        chanid : int - the id of the channel
        user : unicode - the name of the user
        message : unicode - the message
        """

    def on_RemoveChannel(self, cmd):
        chanid, i = self.decode_number(cmd, 0, "!i")
        self.onRemoveChannel(chanid)

    def onRemoveChannel(self, chanid):
        """
        Event telling us that a channel was removed
        chanid : int - the id of the channel
        """

    def on_AddChannel(self, cmd):
        channame, i = self.decode_string(cmd, 0)
        chanid, i = self.decode_number(cmd, i, "!i")
        self.onAddChannel(chanid, channame)

    def onAddChannel(self, chanid, channame):
        """
        Event telling us that a channel was removed
        chanid : int - the id of the channel
        channame : unicode - the name of the channel
        """

    def on_HtmlChannel(self, cmd):
        chanid, i = self.decode_number(cmd, 0, "!i")
        message, i = self.decode_string(cmd, i)
        self.onHtmlChannel(chanid, message)
        
    def onHtmlChannel(self, chanid, message):
        """
        Event telling us that a html message was sent to a channel
        """

    ### Global events

    def on_SendPM(self, cmd):
        playerid, i = self.decode_number(cmd, 0, "!i")
        message, i = self.decode_string(cmd, i) 
        self.onSendPM(playerid, message)

    def onSendPM(self, playerid, message):
        """
        Event telling us of a private message
        playerid : int - the id of the sender
        message : unicode - the actual message
        """

    def on_Away(self, cmd):
        playerid, i = self.decode_number(cmd, 0, "!i")
        status, i = self.decode_number(cmd, i, "B")
        self.onAway(playerid, status>0)

    def onAway(self, playerid, isAway):
        """
        Event telling us that some player changed away status
        playerid : int - the id of the player
        isAway : Boolean - is the player away
        """

    def on_SendMessage(self, cmd):
        network_flags, i = self.decode_number(cmd, 0, "B") 
        hasChannel = network_flags & 1 > 0
        hasId = network_flags & 2 > 0
        data_flags, i = self.decode_number(cmd, i, "B") 
        isHtml = data_flags & 1 > 0
        kwargs = {'isHtml': isHtml, 'hasChannel': hasChannel, 'hasId': hasId}
        if hasChannel: # hasChannel:
            channel, i = self.decode_number(cmd, i, "!I")
            kwargs['channel'] = channel
        if hasId: # hasId:
            id, i = self.decode_number(cmd, i, "!I")
            kwargs['id'] = id
        message, i = self.decode_string(cmd, i)

        if not hasId:
            splitted = message.split(":", 1)
            if len(splitted) == 2:
                kwargs['user'] = splitted[0]
                message = splitted[1].lstrip()
            else:
                kwargs['user'] = ""
                
        self.onSendMessage(message, **kwargs)

    def onSendMessage(self, message, hasId=False, hasChannel=False, isHtml=False, id=0, channel=0, user=None):
        """
        Event telling us of a server wide message
        message - unicode : the real message
        kwargs - 'hasId' -> if True also 'id'
                 'hasChannel' -> if True also 'channel'
                 'isHtml' -> true if should not be escaped
        """

NetworkEvents = {
        'ZipCommand': 0,
        'Login': 1,
        'Reconnect': 2,
        'Logout': 3,
        'SendMessage': 4,
        'PlayersList': 5,
        'SendTeam': 6,
        'ChallengeStuff': 7,
        'EngageBattle': 8,
        'BattleFinished': 9,
        'BattleMessage': 10,
        'BattleChat': 11,
        'KeepAlive': 12,
        'AskForPass': 13,
        'Register': 14,
        'PlayerKick': 15,
        'PlayerBan': 16,
        'ServNumChange': 17,
        'ServDescChange': 18,
        'ServNameChange': 19,
        'SendPM': 20,
        'Away': 21,
        'GetUserInfo': 22,
        'GetUserAlias': 23,
        'GetBanList': 24,
        'CPBan': 25,
        'CPUnban': 26,
        'SpectateBattle': 27,
        'SpectatingBattleMessage': 28,
        'SpectatingBattleChat': 29,
        'VersionControl': 33,
        'TierSelection': 34,
        'ServMaxChange': 35,
        'FindBattle': 36,
        'ShowRankings': 37,
        'Announcement': 38,
        'CPTBan': 39,
        'PlayerTBan': 41,
        'BattleList': 43,
        'ChannelsList': 44,
        'ChannelPlayers': 45,
        'JoinChannel': 46,
        'LeaveChannel': 47,
        'ChannelBattle': 48,
        'RemoveChannel': 49,
        'AddChannel': 50,
        'ChanNameChange': 52,
        'ServerName': 55,
        'SpecialPass': 56,
        'ServerListEnd': 57,
        'SetIP': 58,
        'ServerPass': 59
}

EventNames = {}
for name,number in NetworkEvents.iteritems():
    EventNames[number] = name;

ChallengeDesc = {
     'Sent': 0,
     'Accepted': 1,
     'Cancelled': 2,
     'Busy': 3,
     'Refused': 4,
     'InvalidTeam': 5,
     'InvalidGen': 6,
     'ChallengeDescLast': 7
};


BattleResult = ["Forfeit", "Win", "Tie", "Close"]

BattleCommands = {   
        'SendOut': 0,
        'SendBack': 1,
        'UseAttack': 2,
        'OfferChoice': 3,
        'BeginTurn': 4,
        'ChangePP': 5,
        'ChangeHp': 6,
        'Ko': 7, 
        'Effective': 8,
        'Miss': 9,
        'CriticalHit': 10, 
        'Hit': 11,
        'StatChange': 12,
        'StatusChange': 13,
        'StatusMessage': 14,
        'Failed': 15,
        'BattleChat': 16,
        'MoveMessage': 17,
        'ItemMessage': 18,
        'NoOpponent': 19,
        'Flinch': 20, 
        'Recoil': 21,
        'WeatherMessage': 22,
        'StraightDamage': 23,
        'AbilityMessage': 24,
        'AbsStatusChange': 25,
        'Substitute': 26,
        'BattleEnd': 27,
        'BlankMessage': 28,
        'CancelMove': 29,
        'Clause': 30, 
        'DynamicInfo': 31, 
        'DynamicStats': 32, 
        'Spectating': 33,
        'SpectatorChat': 34,
        'AlreadyStatusMessage': 35,
        'TempPokeChange': 36,
        'ClockStart': 37, 
        'ClockStop': 38, 
        'Rated': 39,
        'TierSection': 40,
        'EndMessage': 41,
        'PointEstimate': 42,
        'MakeYourChoice': 43,
        'Avoid': 44,
        'RearrangeTeam': 45,
        'SpotShifts': 46
}

BattleCommandNames = [0] * len(BattleCommands)
for name,number in BattleCommands.iteritems():
    BattleCommandNames[number] = name;


TempPokeChange = {
        'TempMove': 0,
        'TempAbility': 1,
        'TempItem': 2,
        'TempSprite': 3,
        'DefiniteForme': 4,
        'AestheticForme': 5,
        'DefMove': 6,
        'TempPP': 7
}

#class Flags(object):
#    def __init__(self, *args):
#        self.data = 0
#        self.set(*args)
#
#    def set(self, *args):
#        for arg in args:
#            self.data |= (1 << self._bits_[arg])
#        return self
#
#    def unset(self, *args):
#        for arg in args:
#            self.data &= ~(1 << self._bits_[arg])
#        return self
#
#    def encode(self):
#        i = 0
#        b = []
#        while i == 0 or self.data >> (i*8):
#            c = self.data >> (i*8)
#            if (self.data >> ((i+1)*8)
#                c |= 1 << 7
#            b.append(struct.pack("B", c)
#            i+=1
#        return "".join(b)

#    def decode(self, data):
#        self.data = 0
#        i = 0
#        c = 0
#        while i == 0 or c & (1 << 7):
#            i+=1

#class NetworkFlags_bits(Flags):
#    _bits_ = {
#      'hasClientType': 0,
#      'hasVersionNumber': 1,
#      'hasReconnect': 2,
#      'hasDefaultChannel': 3,
#      'hasAdditionalChannels': 4,
#      'hasColor': 5,
#      'hasTrainerInfo': 6,
#      'marker1': 7,
#      'hasTeams': 8,
#      'hasEventSpecification': 9,
#      'hasPluginList': 10
#    }
#class NetworkFlags(ctypes.Union):
#    _fields_ = [("b", NetworkFlags_bits),
#                ("asbytes", c_uint16)]
#    def __init__(self):
#        self.b.marker1 = True

#class DataFlags_bits(ctypes.BigEndianStructure):
#    _fields_ = [
#      ('supportsZipCompression', c_uint8, 1),
#      ('showTeam', c_uint8, 1),
#      ('isLadderEnabled', c_uint8, 1),
#      ('isIdle', c_uint8, 1),
#      ('wantsIdsWithMessage', c_uint8, 1)
#    ]
#class DataFlags(ctypes.Union):
#    _fields_ = [("b", DataFlags_bits),
#                ("asbytes", c_uint8)]

### Structs used in Pokemon Online Protocol

class Color(object):
    def __init__(self, color_spec=0, alpha=0, red=0, green=0, blue=0, pad=0):
        self.color_spec = 0
        self.alpha = 0
        self.red = 0
        self.green = 0
        self.blue = 0
        self.pad = 0

    def __repr__(self):
        return "<POProtocol.Color (spec=%d, alpha=%d, red=%d, blue=%d, green=%d, pad=%d)>" % (self.color_spec, self.alpha, self.red, self.blue, self.green, self.pad)

class PlayerInfo(object):
    def __init__(self):
        self.id = 0
        self.name = ""
        self.info = ""
        self.auth = 0
        self.flags = 0
        self.rating = 0
        self.pokemon = [0]*6
        self.avatar = 0
        self.tier = ""
        self.color = 0
        self.gen = 0
        self.away = False
        self.channels = {}

    def update(self, o):
        if self.id != o.id:
            raise "Updating with different ID!"
        self.name = o.name
        self.info = o.info
        self.auth = o.auth
        self.flags = o.flags
        self.rating = o.rating
        self.pokemon = o.pokemon
        self.avatar = o.avatar
        self.tier = o.tier
        self.color = o.color
        self.gen = o.gen
        self.away = o.away

    def __repr__(self):
        return "<POProtocol.PlayerInfo (id=%d, name=%r)>" % (self.id, self.name)

class FullInfo(object):
    def __init__(self):
        self.team = 0 # TrainerTeam
        self.ladder = False # Bool
        self.showteam = False # Bool
        self.nameColor = 0 # Color

class TrainerTeam(object):
    def __init__(self):
        self.nick = ""
        self.info = ""
        self.lose = ""
        self.win = ""
        self.avatar = 0
        self.defaultTier = ""
        self.team = Team()
    def __repr__(self):
        return "<POProtocol.TrainerTeam (nick=%r, team=%r)>" % (self.nick, self.team)

class Team(object):
    def __init__(self):
        self.gen = 0
        self.poke = [0]*6
        for k in xrange(6):
            self.poke[k] = PokePersonal() 
    def __repr__(self):
        return "<POProtocol.Team (gen=%d, team=%r)>" % (self.gen, self.poke)

class PokePersonal(object):
    def __init__(self):
        self.uniqueid = PokeUniqueId()
        self.nickname = ""
        self.item = 0
        self.nature = 0
        self.gender = 0
        self.shiny = 0
        self.happiness = 0
        self.level = 0
        self.move = [0]*4
        self.dv = [0]*6
        self.ev = [0]*6
    def __repr__(self):
        return "<POProtocol.PokePersonal (uniqueid=%r, nickname=%s)>" % (self.uniqueid, self.nickname)

class PokeUniqueId(object):
    def __init__(self, pokenum=0, subnum=0):
        self.pokenum = pokenum
        self.subnum = subnum
    def __repr__(self):
        return "<POProtocol.PokeUniquiId (pokenum=%d, subnum=%d)>" % (self.pokenum, self.subnum)

class ChallengeInfo(object):
    def __init__(self, dsc = 0, opp = 0, clauses = 0, mode = 0):
        self.dsc = dsc
        self.opp = opp
        self.clauses = clauses
        self.mode = mode
    def __repr__(self):
        return "<POProtocol.ChallengeInfo (dsc=%d, opp=%d, clauses=%d, mode=%d)>" % (self.dsc, self.opp, self.clauses, self.mode)

class BattleConfiguration(object):
    def __init__(self):
        self.gen = 0
        self.mode = 0
        self.id = [0, 0]
        self.clauses = 0
    def __repr__(self):
        return "<POProtocol.BattleConfiguration (gen=%d, mode=%d, id=%r, clauses=%d)>" % (self.gen, self.mode, self.id, self.clauses)

class TeamBattle(object):
    def __init__(self):
        self.m_pokemons = [None]*6
    def __repr__(self):
        return "<POProtocol.TeamBattle (m_pokemons=%r)>" % (self.m_pokemons)

class PokeBattle(object):
    def __init__(self):
        self.num = PokeUniqueId()
        self.nick = ""
        self.totalLifePoints = 0
        self.lifePoints = 0
        self.gender = 0
        self.shiny = False
        self.item = 0
        self.ability = 0
        self.happiness = 0
        self.normal_stats = [0]*5
        self.move = [0]*4
        self.evs = [0]*6
        self.dvs = [0]*6
    def __repr__(self):
        return "<POProtocol.PokeBattle (num=%r, nick=%r)>" % (self.num, self.nick)

class ShallowShownTeam(object):
    def __init__(self):
        self.pokes = [None]*6
    def __repr__(self):
        return "<POProtocol.ShallowShownTeam>"

class ShallowShownPoke(object):
    def __init__(self):
        self.item = False
        self.num = PokeUniqueId()
        self.level = 0
        self.gender = 0

class BattleChoice(object):
    def __init__(self):
        self.slot = 0
        self.type = 0

    def __repr__(self):
        return "<POProtocol.BattleChoice (type=%r, slot=%r)>" % (self.type, self.slot)

class BattleMove(object):
    def __init__(self):
        self.num = 0
        self.PP = 0
        self.totalPP = 0
    def __repr__(self):
        return "<POProtocol.BattleMove (num=%d, PP=%d, totalPP=%d)>" % (self.num, self.PP, self.totalPP)

class BattleStats(object):
    def __init__(self):
        self.stats = [0]*6

class BattleDynamicInfo(object):

    def __init__(self):
        self.boosts = [0]*7
        self.flags = 0

    def get_flags(self):
        return [self.Flags[flag] for flag in self.Flags if (self.flags & flag) > 0]

    Flags = {
        1:  "Spikes",
        2:  "SpikesLV2",
        4:  "SpikesLV3",
        8:  "StealthRock",
        16: "ToxicSpikes",
        32: "ToxicSpikesLV2" }


class ShallowBattlePoke(object):
    def __init__(self):
        self.num = PokeUniqueId()
        self.nick = ""
        self.lifePercent = 0
        self.fullStatus = 0
        self.level = 0
        self.gender = 0
        self.shiny = False

class Channel(object):
    def __init__(self, chanid, channame):
        self.id = chanid
        self.name = channame
        self.players = {}
    def __repr__(self):
        return "<POProtocol.Channel (id=%d, name=%r, playercount=%d)>" % (self.id, self.name.encode('utf-8'), len(self.players))

class Battle(object):
    def __init__(self, battleid, enemyid, battleconf, myteam):
        self.id = battleid
        self.enemy = enemyid
        self.conf = battleconf
        self.team = myteam

    def __repr__(self):
        return "<POProtocol.Battle (id=%d, enemy=%d, team=%r)>" % (self.id, self.enemy, self.team)
