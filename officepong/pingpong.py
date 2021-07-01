import zulip

#place zuliprc file in /officepong
client = zulip.Client(config_file="zuliprc")

def post(player1, player2, score1, score2, change):
        request = {
            "type": "stream",
            "to": "Bordtennis",
            "topic": "Games",
            #"content": "test string"
            "content": str(player1)[2:-2] + " beat " + str(player2)[2:-2] + "\n" + str(score1) + " to " + str(score2) + " for " + str(round(change,1)) + " points"
        }
        
        result = client.send_message(request)
        print(result)
