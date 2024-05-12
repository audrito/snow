import random
import string
import emoji
import langdetect

# List of funny replies for blank messages
reply_list = (
    "Sometimes we all need a moment of silence.",
    "Did you write that message in invisible ink? I like it.",
    "I appreciate your minimalist approach to communication. Less is more, right?",
    "'Silence is golden.' So, guess it's a golden compliment.",
    "Did you just send me the world's shortest novel? I'm hooked! What happens next?!",
    "Uh oh, did we lose our connection? Hello?! Anyone there?",
    "Wow, that was fast! A new record for silence.",
    "Is this what fancy people call 'quality silence'?",
    "Look at all these empty words!",
    "You know, sometimes saying nothing at all says everything.",
    "In a world full of noise, appreciate the quiet moments.",
    "Blank spaces give us room to imagine and create. Yours made me think of a unicorn eating ice cream!",
    "A moment of silence never hurt anyone. Unless you were expecting more, sorry to disappoint!",
    "Sometimes less is more. This message definitely proves it.",
    "I'm assuming your sudden silence means yes or no, right? Works either way!",
    "Silence can speak volumes. In your case, it whispered the word 'boredom.'",
    "Why do we feel compelled to fill awkward silences with meaningless chatter?",
    "Are you practicing meditation?",
    "You're giving me trust issues - how do I know you didn't accidentally hit send?",
    "Your silence got me wondering - am I even real?",
    "Is this a new form of Morse code? I'm not fluent yet.",
    "Whaat?",
    "yeah?",
    "...",
    "hmm..",
    "thinking deep huh?",
    "Wow, that's quite the thought-provoking message you sent! I'm still pondering its deep meaning.",
    "I was about to reply with something clever, but your message beat me to it!",
    "Well, this is certainly a conversation starter... or ender?",
    "You know what they say, 'a picture is worth a thousand words,' so I guess a blank message is worth a thousand thoughts?",
    "Looks like we have a minimalist over here!",
    "Wow, you must have had a lot to say that you couldn't even fit one word in there.",
    "If messages could talk, this one would be completely silent.",
    "This is definitely a new record for brevity in messaging.",
    "Sometimes less is more...",
    "Are you trying to save on data usage by sending blank messages now?",
    "Clearly, you're a person of few words - I respect that.",
    "A moment of quiet reflection never hurt anyone, right?",
    "I didn't realize meditation was part of our chat session today.",
    "You've left me speechless... literally.",
    "Is this some sort of existential crisis you're having?",
    "Are you practicing your disappearing act through messaging now?",
    "A moment of contemplation is nice every once in a while.",
    "Your message is like a blank canvas, waiting for me to fill it with words.",
    "Do you need help saying something?",
    "I see you've mastered the art of efficiency in communication.",
    "I think we might be reaching a new level of understanding without speaking.",
    "Your message is so empty, yet somehow full of potential meanings.",
    "Well, this is unexpectedly intriguing.",
    "Is this a test of my observation skills?"
)

emoji_replies = (
    "I'm sorry, but I don't speak emoji. Could you please use words?",
    "Emojis are fun, but I need actual words to communicate with you.",
    "I see you're trying to communicate with me using hieroglyphics. Let me get my decoder ring!",
    "I'm not sure what those symbols mean, but I'm sure you can express yourself better with words."
)

def validate(text):
    if all(char in string.punctuation + string.digits or char in emoji.EMOJI_DATA for char in text):
        return random.choice(emoji_replies)

    result = langdetect.detect_langs("hey man, i'm doing great.")[0]

    if not (result.lang == 'en' or result.prob < 0.88):
        return "I don't understand languages other than English yet."
    elif not text.strip():
        return random.choice(reply_list)
    else:
        return True


if __name__ == "__main__":
    print(blank_message_reply())
