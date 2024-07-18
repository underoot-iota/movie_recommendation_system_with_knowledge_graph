import streamlit as st
import pickle
import pandas as pd
import requests
from streamlit_star_rating import st_star_rating
import networkx as nx
from pyvis.network import Network
import json
import numpy as np
TMDB_API = "a1107cc0458955086e008f491fef07a2"
TMDB_ENDPONT = "https://api.themoviedb.org/3/movie"

unExploredThings = dict()
sizeMap = dict()
moviesSize = dict()
initialMovies = dict()
actor="actor"
genre="genre"
director="director"
language="language"
movie="movie"
parameters = {
    "api_key": TMDB_API,
    "language": "en-US",
}


def parse_json(json_str):
    try:
        json_str = json_str.replace("'",'"')
        return json.loads(json_str)
    except:
        return None

def exponential_weight(percentile, exponent=2):
    weight = np.exp(-exponent * ((percentile/100) ** 2))
    weight = weight * 3  # Adjust scaling factor as needed
    weight = max(0, min(weight, 10))
    return weight

def fetch_poster(movie_id):
    poster_url = f"{TMDB_ENDPONT}/{movie_id}"
    response = requests.get(url=poster_url, params=parameters)
    data = response.json()
    return f"https://image.tmdb.org/t/p/w500/{data['poster_path']}"

@st.cache_resource
def loadMovieMap():
    movieMap = pickle.load(open("movieMap.pickle","rb"))
    return movieMap

@st.cache_resource
def loadSortedVoteCount():
    voteCount = pickle.load(open("voteCount.pickle","rb"))
    return voteCount

@st.cache_resource
def loadMoviesListMap():
    moviesListMap = pickle.load(open("moviesListMap.pickle","rb"))
    return moviesListMap

@st.cache_resource
def loadNamesMap():
    namesMap = pickle.load(open("namesMap.pickle","rb"))
    return namesMap

@st.cache_resource
def loadMovieOptions():
    movie_options = [(movieID, movie["original_title"]) for (movieID,movie) in movieMap.items()]
    return movie_options

def getPercentile(value):
    value_index = np.searchsorted(voteCount, value)
    percentile = (value_index / (len(voteCount) - 1)) * 100
    return percentile


movieMap = loadMovieMap()
namesMap = loadNamesMap()
moviesListMap = loadMoviesListMap()
movie_options = loadMovieOptions()
voteCount = loadSortedVoteCount()


def format_movie(movie):
  movie_id, movieTitle = movie  # Assuming movie is a tuple (id, title)
  return movieTitle

def getIncrementOnRating(rating):
    if rating >= 4:
        return 3
    elif rating >=3:
        return 2
    elif rating >=2.5:
        return 1
    elif rating >=2:
        return 0.5
    return 0.25

def getNormalizedSize(size,average):
    val = size*40
    return val/average

def generateMovieRecommendationGraph(userWatchedMovies,isEnabled):
    unExploredThings = dict()
    moviesSize = dict()
    initialMovies = dict()
    for watchedMovieID,rating in userWatchedMovies.items():
        movieData = movieMap[watchedMovieID]
        increase = getIncrementOnRating(rating)
        moviesSize[watchedMovieID] = 25
        initialMovies[watchedMovieID] = True
        for item in movieData["genres"]:
            genreDict = {"id":item["id"],"type":genre}
            if str(genreDict) in unExploredThings:
                unExploredThings[str(genreDict)]+=increase
            else:
                unExploredThings[str(genreDict)] = increase
        for item in movieData["cast"]:
            actorDict = {"id":item["id"],"type":actor}
            if str(actorDict) in unExploredThings:
                unExploredThings[str(actorDict)]+=increase
            else:
                unExploredThings[str(actorDict)]=increase
        directorID = ""
        directorName = ""
        for key,value in movieData["director"].items():
            if key == "id":
                directorID = value
            else:
                directorName = value
        directorDict = {"id":directorID,"type":director}
        if str(directorDict) in unExploredThings:
                unExploredThings[str(directorDict)]+=increase
        else:
            unExploredThings[str(directorDict)]=increase
        for item in movieData["spoken_languages"]:
            languageDict = {"id":item["iso_639_1"],"type":language}
            if str(languageDict) in unExploredThings:
                unExploredThings[str(languageDict)]+=increase
            else:
                unExploredThings[str(languageDict)]=increase
    for key,count in unExploredThings.items():
        row = parse_json(key)
        tagID = row["id"]
        tagType = row["type"]
        moviesList = moviesListMap[tagType][tagID]
        for movieID in moviesList:
            if movieID in initialMovies:
                continue
            if movieID not in moviesSize:
                moviesSize[movieID] = 0
            moviesSize[movieID] += sizeMap[tagType]*count
    if isEnabled:
        for key,count in moviesSize.items():
            movieVoteCount = movieMap[key]["vote_count"]
            percentile = getPercentile(movieVoteCount)
            moviesSize[key] = moviesSize[key]*exponential_weight(percentile)
    sorted_dict = dict(sorted(moviesSize.items(), key=lambda item: item[1], reverse=True))
    G = nx.Graph()
    alreadyMarked = dict()

    for movieID,rating in userWatchedMovies.items():
        movieData = movieMap[movieID]
        movieKey = {"id": movieData["id"],"type":movie}
        movieKey = str(movieKey)
        if movieKey in alreadyMarked:
            continue
        alreadyMarked[movieKey] = True
        G.add_node(movieData["original_title"],type=movie,size=15,initial ="yes")
        for item in movieData["genres"]:
            genreDict = {"id":item["id"],"type":genre}
            genreDict = str(genreDict)
            if genreDict not in alreadyMarked:
                alreadyMarked[genreDict] = True
    #             G.add_node(item["name"],type=genre)
        for item in movieData["cast"]:
            actorDict = {"id":item["id"],"type":actor}
            actorDict = str(actorDict)
            if actorDict not in alreadyMarked:
                alreadyMarked[actorDict] = True
    #             G.add_node(item["name"],type=actor)
        directorID = ""
        directorName = ""
        for key,value in movieData["director"].items():
            if key == "id":
                directorID = value
            else:
                directorName = value
        directorDict = {"id":directorID,"type":director}
        directorDict = str(directorDict)
        if directorDict not in alreadyMarked:
            alreadyMarked[directorDict] = True
    #         G.add_node(directorName,type=director)
        for item in movieData["spoken_languages"]:
            languageDict = {"id":item["iso_639_1"],"type":language}
            languageDict = str(languageDict)
            if languageDict not in alreadyMarked:
                alreadyMarked[languageDict] = True
    #             G.add_node(item["name"],type=language)
    # Add movies, directors, and actors as nodes
    nodeCreated = dict()
    count = 20
    totalSize=0
    for key,value in sorted_dict.items():
        movieKey = {"id": key,"type":movie}
        movieKey = str(movieKey)
        if movieKey in alreadyMarked:
            continue
        totalSize += value
        count -=1
        if count == 0:
            break
    count = 20
    average = totalSize/20
    for key, value in sorted_dict.items():
        movieData = movieMap[key]
        movieKey = {"id": key,"type":movie}
        movieKey = str(movieKey)
        if movieKey in alreadyMarked:
            continue
        alreadyMarked[movieKey] = True
        G.add_node(movieData["original_title"],type=movie,size=getNormalizedSize(value,average),initial="no")
        for item in movieData["genres"]:
            genreDict = {"id":item["id"],"type":genre}
            genreDict = str(genreDict)
            if genreDict in alreadyMarked:
                if genreDict not in nodeCreated:
                    nodeCreated[genreDict] = True
                    G.add_node(item["name"],type=genre)
                    for movieID in moviesListMap[genre][item["id"]]:
                        if movieID in initialMovies:
                            G.add_edge(movieMap[movieID]["original_title"],item["name"])
                G.add_edge(movieData["original_title"],item["name"])
        for item in movieData["cast"]:
            actorDict = {"id":item["id"],"type":actor}
            actorDict = str(actorDict)
            if actorDict in alreadyMarked:
                if actorDict not in nodeCreated:
                    nodeCreated[actorDict] = True
                    G.add_node(item["name"],type=actor)
                    for movieID in moviesListMap[actor][item["id"]]:
                        if movieID in initialMovies:
                            G.add_edge(movieMap[movieID]["original_title"],item["name"])
                G.add_edge(movieData["original_title"],item["name"])
        directorID = ""
        directorName = ""
        for key,value in movieData["director"].items():
            if key == "id":
                directorID = value
            else:
                directorName = value
        directorDict = {"id":directorID,"type":director}
        directorDict = str(directorDict)
        if directorDict in alreadyMarked:
            if directorDict not in nodeCreated:
                nodeCreated[directorDict] = True
                G.add_node(directorName,type=director)
                for movieID in moviesListMap[director][directorID]:
                    if movieID in initialMovies:
                        G.add_edge(movieMap[movieID]["original_title"],directorName)
            G.add_edge(movieData["original_title"],directorName)
        for item in movieData["spoken_languages"]:
            languageDict = {"id":item["iso_639_1"],"type":language}
            languageDict = str(languageDict)
            if languageDict in alreadyMarked:
                if languageDict not in nodeCreated:
                    nodeCreated[languageDict] = True
                    G.add_node(item["name"],type=language)
                    for movieID in moviesListMap[language][item["iso_639_1"]]:
                        if movieID in initialMovies:
                            G.add_edge(movieMap[movieID]["original_title"],item["name"])
                G.add_edge(movieData["original_title"],item["name"])
        count -=1
        if count == 0:
            break

    # Create a pyvis network
    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white")
    net.set_options("""
    var options = {
    "physics": {
        "enabled": true,
        "barnesHut": {
        "centralGravity": 0.1,
        "damping": 0.5,
        "springLength": 500,
        "avoidOverlap": 1,
        "nodeDistance": 300
        },
        "stabilization": {
            "iterations": 2000
        },
        "solver": "barnesHut"
    }
    }
    """)


    # Add nodes
    for node in G.nodes():
        if G.nodes[node]['type'] == actor:
            net.add_node(node, label=node, color="#FFA500")
        elif G.nodes[node]['type'] == director:
            net.add_node(node, label=node, color="#00FFFF")
        elif G.nodes[node]['type'] == language:
            net.add_node(node, label=node, color="#00FF00")
        elif G.nodes[node]['type'] == genre:
            net.add_node(node, label=node, color="#FF00FF")
        else:
            if G.nodes[node]["initial"]=="yes" :
                net.add_node(node, label=node, color="#FF4500",size = 35)
            else:
                net.add_node(node, label=node, color="#FF69B4",size = G.nodes[node]['size'])

    # Add edges
    for edge in G.edges():
        net.add_edge(edge[0], edge[1])
    # Show the network
    # net.toggle_physics(True)
    # net.show_buttons(filter_=['physics'])
    net.save_graph('graph.html')
    return sorted_dict


st.title("Movie Recommender System")
actorWeight = st.slider('Actor Preference', min_value=0.0, max_value=7.0,value = 4.0)
directorWeight = st.slider('Director Preference', min_value=0.0, max_value=5.0,value = 1.0)
genreWeight = st.slider('Genre Preference', min_value=0.0, max_value=5.0,value = 2.0)
languageWeight = st.slider('Language Preference', min_value=0.0, max_value=5.0,value = 0.5)
is_enabled = st.checkbox("Enable Niche Content Booster")

selected_movies = st.multiselect("Select Movies:", options= movie_options,format_func = format_movie)
selected_movie_ratings = {}
if selected_movies:
  st.write("Selected Movies:")
  for (movie_id,movieTitle) in selected_movies:
    rating = st_star_rating(movieTitle, maxValue=5, defaultValue=3, key=movie_id)
    selected_movie_ratings[movie_id] = rating
    st.write("---")

if st.button("Recommend"):
    sizeMap[actor] = actorWeight
    sizeMap[director] = directorWeight
    sizeMap[genre] = genreWeight
    sizeMap[language] = languageWeight
    sorted_dict = generateMovieRecommendationGraph(selected_movie_ratings,is_enabled)
    html_data=""
    with open("./graph.html",'r') as f: 
        html_data = f.read()
    st.header("Recommendation Graph")
    st.components.v1.html(html_data,height=800)
    st.header("Top Recommenedations")
    count = 20
    for key,value in sorted_dict.items():
        movieData= movieMap[key]
        st.write(20-count + 1,movieData["original_title"],value)
        count-=1
        if count == 0:
            break
    # names, posters = recommend_movie(selected_movie_name)

    # col1, col2, col3, col4, col5 = st.columns(5)

    # with col1:
    #     st.text(names[0])
    #     st.image(posters[0])
    # with col2:
    #     st.text(names[1])
    #     st.image(posters[1])
    # with col3:
    #     st.text(names[2])
    #     st.image(posters[2])
    # with col4:
    #     st.text(names[3])
    #     st.image(posters[3])
    # with col5:
    #     st.text(names[4])
    #     st.image(posters[4])
