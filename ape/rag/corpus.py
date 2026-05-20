"""
Seed knowledge base for the multi-domain RAG demo.

Four deliberately-distinct domains so retrieval isolation is easy to verify:
cricket, it, movies, travel. Each doc is a short, self-contained fact passage.
These are intentionally small and hand-written — the point is to exercise the
retrieval + domain-routing path end to end, not to be an encyclopedia.

Shape: DOMAIN -> list of {id, title, text}. `id` is globally unique
(prefixed with the domain) so one Chroma collection can hold all domains and
filter by the `domain` metadata field.
"""

from __future__ import annotations

from typing import Dict, List

KNOWLEDGE: Dict[str, List[Dict[str, str]]] = {
    "cricket": [
        {"id": "cricket_formats", "title": "Formats of cricket",
         "text": "International cricket is played in three main formats: Test "
                 "matches (up to five days, two innings per side), One Day "
                 "Internationals (ODIs, 50 overs per side), and Twenty20 (T20, "
                 "20 overs per side). T20 is the shortest and most explosive format."},
        {"id": "cricket_tendulkar", "title": "Sachin Tendulkar",
         "text": "Sachin Tendulkar of India is the only player to score 100 "
                 "international centuries and holds the record for most runs in "
                 "both Test and ODI cricket. He is nicknamed the 'Little Master'."},
        {"id": "cricket_worldcup", "title": "Cricket World Cup",
         "text": "The ICC Men's Cricket World Cup is the premier ODI tournament, "
                 "held every four years. Australia has won it the most times. "
                 "India won in 1983 and 2011; England won their first title in 2019."},
        {"id": "cricket_roles", "title": "Player roles",
         "text": "A cricket team mixes batters, bowlers, all-rounders, and one "
                 "wicketkeeper. Bowlers are broadly pace (fast) or spin. An "
                 "all-rounder contributes meaningfully with both bat and ball."},
        {"id": "cricket_dismissals", "title": "Ways to get out",
         "text": "Common dismissals are bowled, caught, leg before wicket (LBW), "
                 "run out, and stumped. The batter leaves the field once dismissed; "
                 "ten dismissals end a team's innings."},
        {"id": "cricket_ipl", "title": "Indian Premier League",
         "text": "The Indian Premier League (IPL) is a franchise T20 league held "
                 "annually in India. It is one of the richest cricket leagues and "
                 "features international stars auctioned to city-based teams."},
        {"id": "cricket_ashes", "title": "The Ashes",
         "text": "The Ashes is a historic Test cricket rivalry between England and "
                 "Australia, contested since 1882. The urn is symbolic; the series "
                 "is among the oldest in international sport."},
        {"id": "cricket_pitch", "title": "The pitch and overs",
         "text": "Cricket is played on a 22-yard pitch. An over consists of six "
                 "legal deliveries bowled by one bowler. Conditions like a green or "
                 "dry pitch heavily influence whether pace or spin dominates."},
    ],
    "it": [
        {"id": "it_python", "title": "Python language",
         "text": "Python is a high-level, interpreted programming language known "
                 "for readable syntax and a vast ecosystem. It is widely used in "
                 "web development, data science, automation, and machine learning."},
        {"id": "it_http", "title": "HTTP and the web",
         "text": "HTTP is the request-response protocol of the web. Clients send "
                 "methods like GET and POST to servers, which reply with status "
                 "codes such as 200 (OK), 404 (Not Found), and 500 (Server Error)."},
        {"id": "it_tcp", "title": "TCP/IP networking",
         "text": "TCP provides reliable, ordered delivery of bytes over IP networks "
                 "using a three-way handshake (SYN, SYN-ACK, ACK). UDP is the "
                 "faster, connectionless alternative used for streaming and games."},
        {"id": "it_db", "title": "SQL vs NoSQL databases",
         "text": "Relational (SQL) databases store structured rows with schemas and "
                 "support joins and transactions. NoSQL stores (document, key-value, "
                 "graph) trade strict schemas for flexibility and horizontal scale."},
        {"id": "it_cloud", "title": "Cloud computing models",
         "text": "Cloud services are grouped as IaaS (raw compute/storage), PaaS "
                 "(managed platforms), and SaaS (ready software). Major providers "
                 "include AWS, Microsoft Azure, and Google Cloud."},
        {"id": "it_git", "title": "Version control with Git",
         "text": "Git is a distributed version-control system. Developers commit "
                 "changes, branch to work in isolation, and merge branches back. "
                 "Remotes like GitHub host shared repositories for collaboration."},
        {"id": "it_containers", "title": "Containers and Docker",
         "text": "Containers package an application with its dependencies so it runs "
                 "consistently across environments. Docker builds images; Kubernetes "
                 "orchestrates many containers across a cluster."},
        {"id": "it_security", "title": "Basic web security",
         "text": "Common web risks include SQL injection, cross-site scripting "
                 "(XSS), and broken authentication. Defenses include input "
                 "validation, parameterized queries, HTTPS, and least-privilege access."},
    ],
    "movies": [
        {"id": "movies_inception", "title": "Inception (2010)",
         "text": "Inception is a 2010 science-fiction thriller written and directed "
                 "by Christopher Nolan, starring Leonardo DiCaprio. It follows "
                 "thieves who steal secrets by entering shared dreams within dreams."},
        {"id": "movies_oscars", "title": "The Academy Awards",
         "text": "The Oscars, presented by the Academy of Motion Picture Arts and "
                 "Sciences, honor cinematic achievement. Best Picture is the top "
                 "award. The ceremony has been held annually since 1929."},
        {"id": "movies_genres", "title": "Film genres",
         "text": "Films span genres such as drama, comedy, action, horror, science "
                 "fiction, and documentary. Many films blend genres; a 'rom-com' "
                 "combines romance and comedy, for example."},
        {"id": "movies_nolan", "title": "Christopher Nolan",
         "text": "Christopher Nolan is a British-American director known for complex, "
                 "non-linear narratives in films like Memento, The Dark Knight, "
                 "Interstellar, Dunkirk, and Oppenheimer."},
        {"id": "movies_studios", "title": "Hollywood studios",
         "text": "Major film studios include Warner Bros., Universal, Disney, "
                 "Paramount, and Sony. Studios finance, produce, and distribute "
                 "films; streaming services have become major producers too."},
        {"id": "movies_godfather", "title": "The Godfather (1972)",
         "text": "The Godfather, directed by Francis Ford Coppola and based on Mario "
                 "Puzo's novel, is a 1972 crime drama about the Corleone mafia "
                 "family. It is widely regarded as one of the greatest films ever."},
        {"id": "movies_animation", "title": "Animation",
         "text": "Animated films are created frame by frame, traditionally by hand "
                 "and now mostly with computers. Studios like Pixar and Studio "
                 "Ghibli are celebrated for storytelling in animation."},
        {"id": "movies_boxoffice", "title": "Box office",
         "text": "Box office measures ticket revenue. Avatar and Avengers: Endgame "
                 "are among the highest-grossing films worldwide. Opening-weekend "
                 "numbers are a key early indicator of a film's commercial success."},
    ],
    "travel": [
        {"id": "travel_passport", "title": "Passports and visas",
         "text": "A passport is a government-issued travel document proving identity "
                 "and nationality. Many countries also require a visa for entry; "
                 "some offer visa-on-arrival or visa-free travel for certain passports."},
        {"id": "travel_packing", "title": "Packing tips",
         "text": "Pack light with versatile layers, keep essentials and medication "
                 "in your carry-on, and check airline baggage limits. Rolling clothes "
                 "saves space and reduces wrinkles."},
        {"id": "travel_paris", "title": "Paris, France",
         "text": "Paris, the capital of France, is famous for the Eiffel Tower, the "
                 "Louvre Museum, and Notre-Dame cathedral. It is a major destination "
                 "for art, cuisine, and fashion."},
        {"id": "travel_jetlag", "title": "Beating jet lag",
         "text": "Jet lag occurs when crossing time zones disrupts your body clock. "
                 "Adjusting sleep before travel, staying hydrated, and getting "
                 "daylight at your destination help you adapt faster."},
        {"id": "travel_tokyo", "title": "Tokyo, Japan",
         "text": "Tokyo is Japan's capital, blending ultramodern districts like "
                 "Shibuya with historic temples. Its efficient train network and "
                 "the JR Pass make getting around convenient for visitors."},
        {"id": "travel_budget", "title": "Budget travel",
         "text": "Budget travelers save by booking flights early, traveling in the "
                 "off-season, using hostels or guesthouses, and eating local street "
                 "food. Public transport is usually cheaper than taxis."},
        {"id": "travel_insurance", "title": "Travel insurance",
         "text": "Travel insurance can cover trip cancellation, medical emergencies, "
                 "and lost luggage. It is especially recommended for international "
                 "trips and adventure activities."},
        {"id": "travel_safety", "title": "Staying safe abroad",
         "text": "Keep copies of important documents, be aware of local scams, "
                 "secure your valuables, and know the local emergency number. "
                 "Registering with your embassy can help in a crisis."},
    ],
}

RAG_DOMAINS = sorted(KNOWLEDGE.keys())
