"""
Handle routes for Flask website
"""
from datetime import datetime
from flask import redirect, render_template, request, url_for, jsonify

from officepong import app, db, elo, pingpong
from officepong.models import Player, Match
from sqlalchemy import func, desc, asc, between



@app.route('/register', methods=['POST'])
def register():
    """ Register a new user by adding them to the database. """
    name = request.form['name']
    if not len(name):
        return redirect(url_for('index'))
    db.session.add(Player(name))
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/add_match', methods=['POST'])
def add_match():
    """
    Store the result of the match in the database and update the players'
    elo scores.
    """

    # Extract fields from request fields
    win_names, lose_names = request.form.getlist('winner'), request.form.getlist('loser')
    win_score, lose_score = int(request.form['win_score']), int(request.form['lose_score'])
    

    # Minimize misclicks
    if lose_score + 2 > win_score or (win_score not in (11, 21) and lose_score + 2 != win_score):
        return redirect(url_for('index'))
    
    
    
    # Don't add score if there's a problem with the names
    if not win_names or not lose_names:
        return redirect(url_for('index'))
    for name in win_names:
        if name in lose_names:
            return redirect(url_for('index'))
    for name in lose_names:
        if name in win_names:
            return redirect(url_for('index'))

    # Map each player to their current elo and #games for easy use below
    players = {}
    for player in db.session.query(Player).all():
        players[player.name] = {'elo': player.elo, 'games': player.games}

    # Figure out the elo and its change for the players
    win_elo = sum([players[name]['elo'] for name in win_names])
    lose_elo = sum([players[name]['elo'] for name in lose_names])
    actual, expected, delta = elo.calculate_delta(win_elo, lose_elo, win_score, lose_score)

    # Update elo and #games for both losers and winners
    for name in win_names:
        e = players[name]['elo'] + delta / len(win_names)
        g = players[name]['games'] + 1
        db.session.query(Player).filter_by(name=name).update({Player.elo: e, Player.games: g})
    for name in lose_names:
        e = players[name]['elo'] - delta / len(lose_names)
        g = players[name]['games'] + 1
        db.session.query(Player).filter_by(name=name).update({Player.elo: e, Player.games: g})

    # Add match to database
    win_str, lose_str = ','.join(win_names), ','.join(lose_names)
    match = Match(win_str, lose_str, win_score, lose_score, actual, expected, delta)
    db.session.add(match)

    db.session.commit()
    pingpong.post(win_names, lose_names, win_score, lose_score, delta)
    return redirect(url_for('index'))


@app.route('/delete', methods=['POST'])
def delete():
    ts = request.form['timestampform']
    #print(ts)
    matchid = Match.query.filter_by(timestamp=ts).first()
    #print(matchid)
    db.session.delete(matchid)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/recalculate', methods=['POST'])
def recalculate():
    """
    Recalculate elo scores
    """
    # Get the initialization of every player in the database
    players = {}
    for player in db.session.query(Player).all():
        players[player.name] = {'elo': Player.elo.default.arg, 'games': Player.games.default.arg}


    # Update eatch match
    for match in db.session.query(Match).order_by(Match.timestamp).all():
        winners = match.winners.split(',')
        losers = match.losers.split(',')
        win_elo = sum([players[name]['elo'] for name in winners])
        lose_elo = sum([players[name]['elo'] for name in losers])
        actual, expected, delta = elo.calculate_delta(win_elo, lose_elo,
                                                      match.win_score, match.lose_score)

        # Update player totals
        for name in winners:
            players[name]['elo'] += delta / len(winners)
            players[name]['games'] += 1
        for name in losers:
            players[name]['elo'] -= delta / len(losers)
            players[name]['games'] += 1

        # Submit match
        args = {Match.actual: actual, Match.expected: expected, Match.delta: delta}
        db.session.query(Match).filter_by(timestamp=match.timestamp).update(args)

    # Update each player's elo and # of games played
    for name in players:
        args = {Player.elo: players[name]['elo'], Player.games: players[name]['games']}
        db.session.query(Player).filter_by(name=name).update(args)

    db.session.commit()
    return redirect(url_for('index'))

@app.route('/get', methods=['GET'])
def get():
# get all players
    if request.method == 'GET':
        players = db.session.query(Player).all()
        players_list = sorted(((player.name) for player in players),
                          reverse=True)
        return jsonify(players= players_list,
                    statusCode= 200,), 200


# GET requests will be blocked
@app.route('/json', methods=['POST'])
def json():

#       {
  #         "win_names": "player1",
  #         "lose_names":"player2",
  #         "win_score":11,
  #         "lose_score":6,
  #         "statusCode": 200
#       }  
    
    request_data = request.get_json()
    
    win_names = None
    lose_names = None
    win_score = None
    lose_score = None

    if request_data:
        if 'win_names' in request_data:
            win_names = request_data['win_names']

        if 'lose_names' in request_data:
            lose_names = request_data['lose_names']
            
        if 'win_score' in request_data:
            win_score = int(request_data['win_score'])
            
        if 'lose_score' in request_data:
            lose_score = int(request_data['lose_score'])
    
    win_names, lose_names = [win_names], [lose_names]
    
    print(win_names)
    print(lose_names)
    print(win_score)
    print(lose_score)
    
    # Minimize misclicks
    if lose_score + 2 > win_score or (win_score not in (11, 21) and lose_score + 2 != win_score):
        return redirect(url_for('index'))

    # Don't add score if there's a problem with the names
    if not win_names or not lose_names:
        return redirect(url_for('index'))
    for name in win_names:
        if name in lose_names:
            return redirect(url_for('index'))
    for name in lose_names:
        if name in win_names:
            return redirect(url_for('index'))

    # Map each player to their current elo and #games for easy use below
    players = {}
    for player in db.session.query(Player).all():
        players[player.name] = {'elo': player.elo, 'games': player.games}

    # Figure out the elo and its change for the players
    win_elo = sum([players[name]['elo'] for name in win_names])
    lose_elo = sum([players[name]['elo'] for name in lose_names])
    actual, expected, delta = elo.calculate_delta(win_elo, lose_elo, win_score, lose_score)

    # Update elo and #games for both losers and winners
    for name in win_names:
        e = players[name]['elo'] + delta / len(win_names)
        g = players[name]['games'] + 1
        db.session.query(Player).filter_by(name=name).update({Player.elo: e, Player.games: g})
    for name in lose_names:
        e = players[name]['elo'] - delta / len(lose_names)
        g = players[name]['games'] + 1
        db.session.query(Player).filter_by(name=name).update({Player.elo: e, Player.games: g})

    # Add match to database
    win_str, lose_str = ','.join(win_names), ','.join(lose_names)
    match = Match(win_str, lose_str, win_score, lose_score, actual, expected, delta)
    db.session.add(match)

    db.session.commit()
    return redirect(url_for('index'))

    



@app.route('/')
def index():
    """
    The main page of the site. Display the dashboard.
    """
    def convert_timestamp(timestamp):
        return datetime.fromtimestamp(int(timestamp)).strftime("%d/%m %HH:%MM")
    def convert_timestamp_day(timestamp):
        return datetime.fromtimestamp(int(timestamp)).strftime("%d/%m")
    
    matches = db.session.query(Match).all()
    players = db.session.query(Player).all()
    days=db.session.query(Match.timestamp, func.count(Match.timestamp)).group_by(func.strftime('%Y-%m-%d', Match.timestamp, 'unixepoch', 'localtime')).all()
    
    #check if query is empty.
    if not days: 
        print('query is empty')
        dayslist = []
        countlist = []
    else:
        dayslist, countlist = zip(*days)
        #print(dayslist)
        #print(countlist)
        
    oldest_wins = db.session.query(Match.winners,func.max(Match.timestamp)).group_by(Match.winners).order_by(asc(Match.timestamp)).all()
    oldest_lost = db.session.query(Match.losers,func.max(Match.timestamp)).group_by(Match.losers).order_by(asc(Match.timestamp)).all()
    
    oldest_games = {}
    old_players =[]

    for player,timestamp in oldest_wins:
	    oldest_games.setdefault(player, timestamp)

    for item in oldest_lost:
        if item[0] in oldest_games.keys():
            if item[1] > oldest_games.get(item[0]):
                oldest_games[item[0]] = item[1]
                
                
                
                
   # Create list of players scores for each day
    playersdict = {}
    scorelist =[]
    for player in db.session.query(Player).all():
        playersdict[player.name] = {'elo': Player.elo.default.arg, 'list': []}

    # Update eatch match
    previousday = 0;
    for count, day in enumerate(dayslist):
        #print(count, convert_timestamp_day(previousday), convert_timestamp_day(day))
        if(count<len(dayslist)-1):
            matchlist = db.session.query(Match).filter(Match.timestamp >= day).filter(Match.timestamp < dayslist[count+1]).all()
        else:
            matchlist = db.session.query(Match).filter(Match.timestamp >= day).all()
        for match in matchlist:
            winners = match.winners.split(',')
            losers = match.losers.split(',')
            win_elo = sum([playersdict[name]['elo'] for name in winners])
            lose_elo = sum([playersdict[name]['elo'] for name in losers])
            actual, expected, delta = elo.calculate_delta(win_elo, lose_elo,
                                                          match.win_score, match.lose_score)

            # Update player totals
            for name in winners:
                playersdict[name]['elo'] += delta / len(winners)
                #playersdict[name]['games'] += 1
            for name in losers:
                playersdict[name]['elo'] -= delta / len(losers)
                #playersdict[name]['games'] += 1
        for name, score in playersdict.items():
            playersdict[name]['list'].append(playersdict[name]['elo'])
        #scorelist.append(playersdict[name]['elo'])
        previousday = day
    #print(playersdict)
            
        
    


    old_players = sorted(oldest_games.items(),key=lambda x:x[1])[:2]

    players_list = sorted(((player.elo, player.name, player.games) for player in players),reverse=True)
    
    return render_template('home.html', matches=matches, players=players_list, playersdict=playersdict,
                           convert_timestamp=convert_timestamp,convert_timestamp_day=convert_timestamp_day, countlist=countlist, dayslist=dayslist, old_players=old_players)
