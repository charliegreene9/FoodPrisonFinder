import ast
import datetime as dt
import os
from pathlib import Path

import geopandas as gp
import streamlit as st
from geopy.distance import geodesic
from streamlit_js_eval import streamlit_js_eval

# Your list of target locations
locations = gp.read_file(Path(os.getcwd(), "locations.json"))
days = {
    0: "Maandag",
    1: "Dinsdag",
    2: "Woensdag",
    3: "Donderdag",
    4: "Vrijdag",
    5: "Zaterdag",
    6: "Zondag",
}


# Define a cleaner function
def safe_literal_eval(string):
    try:
        # Replace smart quotes with straight ones
        s_clean = (
            string.replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
        )
        return ast.literal_eval(s_clean)
    except Exception as e:
        print(f"Error parsing: {string} → {e}")
        return None


# Function to find the closest location
def find_closest(user_location, gdf):
    # Add a distance column
    gdf["distance_km"] = gdf["geometry"].apply(
        lambda point: geodesic(user_location, (point.y, point.x)).kilometers
    )
    # Get the closest
    closest_row = gdf.loc[gdf["distance_km"].idxmin()]
    return closest_row


def is_it_open(df, days):
    # Checking which day it is and getting open and close times for today
    today = days[dt.datetime.today().weekday()]
    now = dt.datetime.now().time()
    print(
        safe_literal_eval(df["Close_time"]), type(safe_literal_eval(df["Close_time"]))
    )
    closing = dt.datetime.strptime(
        safe_literal_eval(df["Close_time"])[today], "%H:%M"
    ).time()
    am = dt.datetime.strptime("07:00", "%H:%M").time()
    opening = dt.datetime.strptime(
        safe_literal_eval(df["Open_time"])[today], "%H:%M"
    ).time()
    time_left = dt.datetime.combine(dt.date.min, opening) - dt.datetime.combine(
        dt.date.min, now
    )
    if (opening > now > closing and closing < am) or (
        now < opening and closing > am
    ):  # (now < opening and closing > midnight) or
        msg = "It looks like you will need to scavenge in your own home tonight!"
    elif now > closing and closing > am:
        time_left += dt.timedelta(days=1)
        msg = f"Go to bed and come back tomorrow, it will open again at {opening}."
    elif (opening < now < closing and closing > am) or (
        opening < now > closing and closing < am
    ):
        if time_left <= dt.timedelta(minutes=20):
            msg = f"""You're not making it this time makker.
            Only {time_left} until closing."""
        elif dt.timedelta(hours=1) > time_left > dt.timedelta(minutes=20):
            msg = f"""Better rush, the kaas souffle is almost finished and
            there is only {time_left} until closing!"""
        elif time_left > dt.timedelta(hours=1):
            msg = "Plenty of time still, another {time_left}."
    return time_left, msg


# Streamlit UI
st.title("📍 Find the closest snackbar")  # TODO: actual structuring


js_code = """
    new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(
            (position) => resolve({
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            }),
            (err) => reject(err)
        );
    })
"""

location = streamlit_js_eval(js_expressions=js_code, key="user_location")

if location:
    if "latitude" in location and "longitude" in location:
        lat = location["latitude"]
        lon = location["longitude"]
        # st.success(f"📍 Your location: ({lat:.5f}, {lon:.5f})")
        closest = find_closest((lat, lon), locations)
        print(closest)
        col1, col2, col3 = st.columns([0.2, 5, 0.2])
        col2.image(
            Path(os.getcwd(), "Assets", "Images", f"{closest['Brand'].lower()}.png"),
            use_container_width=True,
            caption="Go forth and free the food from its prison",
        )
        col2.write(f"## ✅ The closest snackbar is... {closest['Name']}!")
        time_left, msg = is_it_open(closest)
        col2.write(f"## It is {closest['distance_km']:,.4g}km away from you right now.")
        col2.write(msg)
    else:
        st.error("❌ Failed to get location.")
else:
    st.warning("Waiting for geolocation permission...")
