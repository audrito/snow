import re
import textwrap


try:
    import spacy
except:
    pass

short_form_dict = {
    "afaik":"as far as I know",
    "afaict":"as far as I can tell",
    "afk":"away from keyboard",
    "asap":"as soon as possible",
    "b4":"before",
    "b4n":"bye for now",
    "bbl":"be back later",
    "bbs":"be back soon",
    "brb":"be right back",
    "bf":"boyfriend",
    "bff":"best friends forever",
    "bfn":"bye for now",
    "btw":"by the way",
    "cya":"see ya",
    "ez":"easy",
    "f2f":"face to face",
    "fb":"facebook",
    "g2g":"got to go",
    "gn":"good night",
    "gr8":"great",
    "fr":"for real",
    "tbh":"to be honest",
    "ngl":"not going to lie",
    "nvm":"nevermind",
    "irl":"in real life",
    "jk":"just kidding",
    "k":"okay",
    "l8r":"later",
    "lmao":"laugh my ass off",
    "lmfao":"laugh my fucking ass off",
    "lol":"laughing out loud",
    "m8":"mate",
    "n1":"nice one",
    "noob":"newbie",
    "nrn":"not right now",
    "ntl":"note to self",
    "ofc":"of course",
    "omfg":"oh my fucking god",
    "omg":"oh my god",
    "ppl":"people",
    "r":"are",
    "rofl":"rolling on the floor laughing",
    "sk8":"skate",
    "smh":"shaking my head",
    "srsly":"seriously",
    "abt":"about",
    "ttul":"talk to you later",
    "ttyl":"talk to you later",
    "ttyt":"talk to you tommorow",
    "u":"you",
    "wth":"with",
    "w/o":"without",
    "w2g":"way to go",
    "w8":"wait",
    "wassup":"what's up",
    "wb":"welcome back",
    "wtf":"what the fuck",
    "wuzup":"what is up",
    "aight":"alright",
    "prblm":"problem",
    "pb":"problem",
    "fav":"favorite",
    "idk":"I don't know",
    "idc":"I don't care",
    "im":"I'm",
    "ik":"I know",
    "yk":"you know",
    "mb":"my bad",
    "myb":"maybe",
    "sry":"sorry",
    "acc":"account",
    "rn":"right now",
    "gd":"good",
    "nb":"not bad",
    "yall":"you all",
    "y'all":"you all",
    "vid":"video",
    "wbu":"what about you",
    "hbu":"how about you",
    "hru":"how are you",
    "nd":"and",
    "n":"and",
    "cz":"cause",
    "ntg":"nothing",
    "srs":"serious",
    "rp":"roleplay",
    "src":"source",
    "gtg":"have to go",
    "em":"them",
    "gurl":"girl",
    "boi":"boy",
    "bout":"about",
    "bt":"but",
    "lil":"little",
    "i'mma":"i'm going to",
    "tryna":"trying to",
    "bby":"baby",
    "bbe":"babe",
    "tiddies":"tits",
    "tiddy":"tit",
    "idgaf":"I don't give a fuck",
    "np":"no problem",
    "dat":"that",
    "phatass":"fat ass",
    "mah":"my",
    "luv":"love",
    "dnt":"don't",
    "wut":"what",
    "da":"the",
    "ily":"I love you",
    "ty":"thank you",
    "ur":"your",
    "lemme":"let me",
    "hbd":"happy birthday",
    "phn":"phone",
    "asl":"age,sex,location",
    "DM":"Direct Message",
    "wyd":"what are you doing",
    "wym":"what you mean",
    "istg":"I swear to god",
    "omw":"on my way",
    "nbd":"no big deal",
    "otoh":"on the other hand",
    "thx":"thanks",
    "tnx":"thanks",
    "hmu":"hit me up",
    "imu":"I miss you",
    "wywh":"wish you were here",
    "ygtr":"you got that right",
    "afaic":"as far as I'm concerned",
    "ly":"love you",
    "4ever":"forever",
    "idm":"I don't mind"
}

# Compile the regular expression pattern for short forms
short_form_pattern = re.compile(
    "\\b(" + "|".join(map(re.escape, short_form_dict.keys())) + ")\\b",
    flags=re.IGNORECASE
)

# Compile the regular expression pattern for role mentions
mention_pattern = re.compile(r'<@[&!]?\d+>\s*')

# Load spaCy model outside of the function
try:
    nlp = spacy.load('en_core_web_sm')
except:
    nlp = None
    print("\033[91mSpaCy model could not be loaded.\033[00m")

def fix_short_forms(text):
    try:
        # Check if the text contains any URL or file path
        if re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text):
            return text

        # Remove role mentions
        text = mention_pattern.sub('', text)

        # Convert the text to lower case
        text = text.casefold()

        # Check if the text contains any short form
        if not short_form_pattern.search(text):
            return text
        else:
            # Replace the short forms
            text = short_form_pattern.sub(
                lambda match: short_form_dict[match.group(0)], 
                text
            )

            # Capitalize the standalone "I"
            text = re.sub(r'\b(i)\b', 'I', text)

            # If the Spacy model is loaded, process the text with Spacy
            if nlp is not None:
                doc = nlp(text)
                text = ''.join(sent.text_with_ws[0].capitalize() + sent.text_with_ws[1:] for sent in doc.sents)

            return text
    except Exception as e:
        print(f"\033[91mCleanput is not working properly: {e}\033[00m")
        return text
