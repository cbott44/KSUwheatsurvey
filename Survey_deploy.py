#==================================================================================================================================
#Streamlit Setup
#==================================================================================================================================
#connection to drop box in 'secrets'
#define color theme in config.toml (streamlit folder github)
#lauch from Streamlit cloud -> my apps

#import modules
import numpy as np
import streamlit as st
import pandas as pd 
import random
import string
import datetime
import os
import dropbox
from io import StringIO
import requests

app_key = st.secrets["dropbox"]["app_key"]
app_secret = st.secrets["dropbox"]["app_secret"]
refresh_token = st.secrets["dropbox"]["refresh_token"]

def get_new_access_token(app_key, app_secret, refresh_token):
    token_url = "https://api.dropboxapi.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    auth = (app_key, app_secret)

    response = requests.post(token_url, data=data, auth=auth)
    response.raise_for_status()
    tokens = response.json()
    return tokens["access_token"]

# Initialize Dropbox client
access_token = get_new_access_token(app_key, app_secret, refresh_token)
dbx = dropbox.Dropbox(access_token)

# Use dbx here
files = dbx.files_list_folder('').entries

#___________________________________________________________________________________________________________________________________________
#___________________________________________________________________________________________________________________________________________
# Define paths here! (set once and use throughout)

#csv for producer data
producer_FILE_PATH = "/streamlit/producers_info.csv"

#csv for field information
field_FILE_PATH = "/streamlit/fields_info.csv"

#folder to save soil test uploads
soil_tests = "/streamlit/soiltest_uploads"

#___________________________________________________________________________________________________________________________________________
#___________________________________________________________________________________________________________________________________________

#Initialize Streamlit app
st.title('Survey of Kansas Irrigated Wheat')

#define the look of info.box
st.markdown("""
    <style>
    .info-box { 
        background-color: #f0f2f6 !important;
        color: black !important;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #d3d3d3;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Write in info box
st.markdown("""
    <div class="info-box">
        <u>Instructions:</u> <br>
        1. Submit the first form with your personal information before proceeding to the second section.<br>
        2. In the second section you will be asked to provide field-specific information. Add as many fields as you would like; <strong> Prioritize adding data from 2023, 2024, and 2025 Harvests</strong>.<br>
        3. If you do not know the answer to a question or it does not pertain to you, leave it blank.<br><br>
        <strong>Funded by the Kansas Wheat Commission and Kansas Crop Improvement Association</strong><br>
        Contact Claire Bott with problems or questions:<br>
        <a href="mailto:cb44@ksu.edu">cb44@ksu.edu</a> &nbsp;&nbsp; (734) 834-7494
    </div>
""", unsafe_allow_html=True)

#Add Background Image
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://www.visitgck.com/wp-content/uploads/2020/06/kansas-wheat-harvest.jpg");
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        padding: 2rem !important;
        background-color: white !important;
        color: black !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

#Define the color of form backgrounds
css = """
<style>
/* ========== FORCE GLOBAL LIGHT MODE ========== */
html, body, .stApp {
    background-color: white !important;
    color: black !important;
}

/* ========== FORM ========== */
[data-testid="stForm"] {
    background: rgb(170,194,206) !important;
    color: black !important;
}

/* ========== EXPANDERS ========== */
/* Expander header */
div[data-testid="stExpander"] > details > summary {
    background-color: #d3d3d3 !important;
    color: black !important;
    border-radius: 0.5rem;
    padding: 0.5rem;
}

/* Expander content */
div[data-testid="stExpander"] > details > div {
    background-color: #d3d3d3 !important;
    color: black !important;
    padding: 1rem;
    border-radius: 0 0 0.5rem 0.5rem;
}

</style>
""" 

#allows rendering HTML
#html is language for structuring webpages, css controls the look of html
st.write(css, unsafe_allow_html=True)

#============================================================================================================================================
#Form 1 - Producer Information
#============================================================================================================================================

#define function to generate unique producer ID (use when submitted)
def generate_unique_id(df, user_firstname, user_lastname):
    """Generate a unique ID or use existing one"""
    #check for existing same name
    existing_row = df[(df['firstname'].str.lower() == user_firstname.lower()) & (df['lastname'].str.lower() == user_lastname.lower())]

    #if found use same ID
    if not existing_row.empty:
        return existing_row.iloc[0]['producer_id']
    else:
        # else generate new ID
        while True:
            producer_id = ''.join(random.choices(string.digits, k=6)) 
            # make sure ID doesn't already exist
            if producer_id not in df['producer_id'].values:
                return producer_id 

#start with no producer ID in session state
if 'producer_id' not in st.session_state:
    st.session_state['producer_id'] = None

#define an empty dictionary
new_data = {
    "firstname": "",
    "lastname": "",
    "phone": "",
    "email": "",
    # "street_address": "",
    # "street_address2": "",
    # "city": "",
    # "zip_code": "",
    "age": "",
    "ed_level": "",
    "producer_id": "",

    'kn_extension_agent': False,
    'kn_prv_consult': False,
    'kn_product_vendor': False,
    'kn_self': False,
    'kn_other': False,

    'irr_wheat_ac': "",
    'farm_size':"",
    "farm_purpose": "",
    #'years_irr': "",
    #'dry_v_irr': "",
    'water_limits': "",
    'statement1':"",
    'statement2':""
}
expected_columns = list(new_data.keys())

#read csv, populate fields if starting empty
# Helper: Read CSV from Dropbox
def read_csv_from_dropbox_safely(path, columns):
    try:
        metadata, res = dbx.files_download(path)
        data = res.content.decode("utf-8").strip()  # Strip whitespace and newlines
        
        if not data:
            return pd.DataFrame(columns=columns)

        # Check that the first line contains headers
        if ',' not in data.splitlines()[0]:
            return pd.DataFrame(columns=columns)

        df = pd.read_csv(StringIO(data))
        return df
    
    except dropbox.exceptions.ApiError as e:
        st.warning(f"Dropbox API error or file not found: {e}")
        return pd.DataFrame(columns=columns)
    
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columns)
df = read_csv_from_dropbox_safely(producer_FILE_PATH, expected_columns)

#---------------------------------------------------------------------------------------------------------------------------------------------------
options_form = st.form("options_form", clear_on_submit = False) #create form, clear fields when data is submitted

with options_form:
    options_form.markdown("### Personal Information")
   
    #text inputs
    left, right = options_form.columns(2)
    new_data['firstname'] = left.text_input("First name")
    new_data['lastname'] = right.text_input("Last name")

    
    new_data['phone'] = options_form.text_input("Phone Number")
    new_data['email'] = options_form.text_input("Email address")

    # #2 column
    # left, right = options_form.columns([2,1], vertical_alignment = "bottom")
    # new_data['street_address'] = left.text_input("Street Address")
    # new_data['street_address2'] = right.text_input("Street Address line 2")

    # #2 columns
    # left, right = options_form.columns(2, vertical_alignment = "bottom")
    # new_data['city'] = left.text_input("City")
    # new_data['zip_code'] = right.text_input("Zip Code")

    left, right = options_form.columns([2,3], vertical_alignment = "bottom")
    new_data['age'] = left.text_input("Age")
    new_data['ed_level'] = right.selectbox("Highest Level of Completed Education",options = ("--","below highschool",
                                "highschool","some college","associates degree","trade/vocational program","bachelors degree","postgraduate degree"))

    #education source
    st.write('Primary Source of Information (select all that apply):')
    new_data['kn_extension_agent'] = options_form.checkbox('Extension Agents')
    new_data['kn_prv_consult'] = options_form.checkbox('Private Consultant')
    new_data['kn_product_vendor'] = options_form.checkbox('Ag. product Vendor')
    new_data['kn_self'] = options_form.checkbox('Own Knowledge')
    new_data['kn_other'] = options_form.checkbox('Other')

    #Farm information
    #options_form.markdown("<hr>", unsafe_allow_html=True) 
    options_form.markdown("**Farm information**")

    left, right = st.columns(2, vertical_alignment = "bottom")
    new_data['farm_size'] = left.text_input("Total Farm Acreage")
    new_data['irr_wheat_ac'] = right.text_input("Average Irrigated Wheat Acreage")

    farm_purpose = options_form.empty()
    placeholder_2 = options_form.empty() #input for other farm purpose
    
    # new_data['years_irr'] = options_form.text_input("Year Spent Irrigating Wheat")
    # new_data['dry_v_irr'] = options_form.radio("Also Grow Dryland Wheat?", options=("Select","yes", "no"), horizontal=True)

    #water limitations
    options_form.markdown("Briefly describe any restrictions faced on water usage?")
    options_form.markdown(
        """
        <div style='margin-bottom: -1000px;'>
            <span style='color:#444; font-size:0.95rem'>e.g. government 5 year flex plan, seasonally dry wells, etc.
        </div>
        """, 
        unsafe_allow_html=True
    )

    new_data['limits'] = options_form.text_area("", height = 68)

    #agreement with the statements
    # options_form.markdown("Rate the following two statements:")
    
    # new_data['statement1'] = options_form.radio(
    # "Managing water sustainably is essential for ensuring that agriculture remains viable in our region for future generations.",
    # options=[
    #     "Select",
    #     "1 - Strongly Disagree",
    #     "2 - Disagree",
    #     "3 - Neutral",
    #     "4 - Agree",
    #     "5 - Strongly Agree"
    #         ]
    #     )

    # new_data['statement2'] = options_form.radio(
    # "Concerns about water availability significantly influence the crops I choose to plant and how I manage my fields.",
    # options=[
    #     "Select",
    #     "1 - Strongly Disagree",
    #     "2 - Disagree",
    #     "3 - Neutral",
    #     "4 - Agree",
    #     "5 - Strongly Agree"
    #         ]
    #     )

    
    #submit buttons
    add_data = options_form.form_submit_button("Submit", type = "primary") #type controls the look
   # clear_form = options_form.form_submit_button("Clear form", type = "secondary")
    
    #Keep message within form bounds
    #CSS for formatting
    if add_data:
        options_form.markdown(
            """
            <div style='background-color: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 20px;'>
                <strong style='color: green;'> Submission Successful:</strong> Continue to Next Section
            </div>
            """,
            unsafe_allow_html=True
        )

#define conditional placeholders for 'other' options 
with farm_purpose:
    selection2 = st.selectbox("Primary Purpose of Farm", options = ("--","Grain","Livestock","50/50","Other"))
with placeholder_2:
    if selection2 == "Other":
        purpose_other = st.text_input("Enter other purpose")


#if form 1 submitted:
if add_data:
    #use the producer ID function
    new_data['producer_id'] = generate_unique_id(df, new_data['firstname'], new_data['lastname'])

    #save producer ID into session state to take to the second form
    st.session_state['producer_id'] = new_data['producer_id']

    #fill farm purpose with 'other'
    purpose_temp = ""
    if selection2 == "Other":
        purpose_temp = purpose_other
    else:
        purpose_temp = selection2

    new_data['farm_purpose'] = purpose_temp
 
    #add to end of csv
    new_df = pd.DataFrame([new_data]) #dictionary to data frame
    df = pd.concat([df, new_df], ignore_index=True) #append to csv
    
    # Save updated DataFrame to Dropbox
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    dbx.files_upload(csv_buffer.getvalue().encode(), producer_FILE_PATH, mode=dropbox.files.WriteMode("overwrite"))

    #Display updated file
    #st.write(df) 


#clear form instead of submitting
#if clear_form:
#   st.rerun()  # Reruns the script and resets everything

#============================================================================================================================================
#Form 2 - Field 1 Information
#nutrient inputs need examples
#============================================================================================================================================

if "field_index" not in st.session_state:
    st.session_state.field_index = 1

field_idx = st.session_state.field_index

# ---------------------------------------------------------------------
# Base dictionary template
def empty_field_dict():
    d = {
        "producer_id": "",
        "field_number": "",
        "yield": "",
        "yield_unit": "",
        "forage_yield": "",
        "forage_unit": "",
        "lat": "",
        "long": "",
        "county_ident": "",
        "section": "",
        "township": "",
        "range": "",
        "field_size": "",
        "field_size_unit": "",
        "crop_purpose": "",
        "prev_crop": "",
        "prev_crop_year": "",
        "prev_crop_purpose": "",
        "prev_crop_irr": "",
        "planting_date": "",
        "harvest_date": "",
        "cultivar": "",
        "seed_source": "",
        "seed_cleaned": "",
        "seed_treat": "",
        "tillage": "",
        "profile_h20": "",
        "row_space": "",
        "seeding_rate": "",
        "seeding_rate_unit": "",
        "impacting_events": "",
        "K_soil": "",
        "P_soil": "",
        "N_soil": "",
        "N_soildepth": "",
        "manure_rate": "",
        "manure_freq": "",
        "fung": "",
        "fungicide_freq": "",
        "fungicide_time": "",
        "fungicide_prod": "",
        "herb": "",
        "herbicide_freq": "",
        "herbicide_time": "",
        "herb_prod": "",
        "insect": "",
        "insecticide_freq": "",
        "insecticide_time": "",
        "insect_prod": "",
        "irrigated": "",
        "irr_shared": "",
        "irr_decision": "",
        "irr_type": "",
        "system_config": "",
        "system_height": "",
        "system_details": "",
        "system_capacity": "",
        "water_source": "",
        "capacity_flux": "",
        "pre_plant_water": ""
    }

    # nutrient products
    for i in range(1, 7):
        for f in [
            "product","rate","time","date","month","plus",
            "nutrient_a","nutrient_a_amnt",
            "nutrient_b","nutrient_b_amnt",
            "nutrient_c","nutrient_c_amnt"
        ]:
            d[f"{i}_{f}"] = ""

    # irrigation events
    for i in range(1, 9):
        for f in ["date","month","timing","amount","rate","fertigation"]:
            d[f"irr{i}_{f}"] = ""

    return d


new_data = empty_field_dict()

# ---------------------------------------------------------------------
# FORM
with st.form(f"field_form_{field_idx}", clear_on_submit=True):

    st.markdown(f"## Field {field_idx} Information")

    # =========================
    # LOCATION
    with st.expander("Field Location"):
        left, right = st.columns(2)
        new_data["lat"] = left.text_input("Latitude", key=f"lat_{field_idx}")
        new_data["long"] = right.text_input("Longitude", key=f"long_{field_idx}")

        new_data["county_ident"] = st.text_input(
            "County & Road", key=f"county_{field_idx}"
        )

        left, mid, right = st.columns(3)
        new_data["section"] = left.text_input("Section", key=f"sec_{field_idx}")
        new_data["township"] = mid.text_input("Township", key=f"twp_{field_idx}")
        new_data["range"] = right.text_input("Range", key=f"rng_{field_idx}")

    # =========================
    # FIELD SIZE
    left, right = st.columns(2)
    new_data["field_size"] = left.text_input("Field Size", key=f"size_{field_idx}")
    new_data["field_size_unit"] = right.selectbox(
        "Unit", ("Acres","Hectares"), key=f"sizeu_{field_idx}"
    )

    # =========================
    # CROP PURPOSE
    cp = st.selectbox(
        "Primary Crop Purpose",
        ("seed","grain","forage","dual-purpose","other"),
        key=f"cp_{field_idx}"
    )
    if cp == "other":
        new_data["crop_purpose"] = st.text_input(
            "Specify other purpose", key=f"cp_o_{field_idx}"
        )
    else:
        new_data["crop_purpose"] = cp

    # =========================
    # PREVIOUS CROP
    left, right = st.columns(2)
    new_data["prev_crop"] = left.text_input("Previous Crop", key=f"pc_{field_idx}")
    new_data["prev_crop_year"] = right.text_input("Harvest Year", key=f"pcy_{field_idx}")
    new_data["prev_crop_purpose"] = st.selectbox(
        "Previous Crop Purpose",
        ("Grain","Seed","Forage","Silage","Other"),
        key=f"pcp_{field_idx}"
    )
    new_data["prev_crop_irr"] = st.radio(
        "Previous crop irrigated?",
        ("yes","no"),
        horizontal=True,
        key=f"pci_{field_idx}"
    )

    # =========================
    # SOIL TESTS
    with st.expander("Soil Testing"):
        left, right = st.columns(2)
        new_data["K_soil"] = left.text_input("K (ppm)", key=f"k_{field_idx}")
        new_data["P_soil"] = right.text_input("P (ppm)", key=f"p_{field_idx}")

        left, right = st.columns(2)
        new_data["N_soil"] = left.text_input("N", key=f"n_{field_idx}")
        new_data["N_soildepth"] = right.text_input("Depth", key=f"nd_{field_idx}")

    # =========================
    # PLANTING / HARVEST
    left, right = st.columns(2)
    new_data["planting_date"] = left.date_input(
        "Planting Date", key=f"pd_{field_idx}"
    )
    new_data["harvest_date"] = right.date_input(
        "Harvest Date", key=f"hd_{field_idx}"
    )

    # =========================
    # YIELD
    left, right = st.columns(2)
    new_data["yield"] = left.text_input("Grain Yield", key=f"y_{field_idx}")
    yu = right.selectbox(
        "Yield Unit", ("bu/ac","lb/ac","kg/ha","other"), key=f"yu_{field_idx}"
    )
    if yu == "other":
        new_data["yield_unit"] = st.text_input(
            "Specify unit", key=f"yuo_{field_idx}"
        )
    else:
        new_data["yield_unit"] = yu

    new_data["impacting_events"] = st.text_area(
        "Yield-impacting events", key=f"impact_{field_idx}"
    )

    # =========================
    # SUBMIT
    add_field = st.form_submit_button("Add another field", type="primary")
    finish = st.form_submit_button("Finish", type="secondary")

# ---------------------------------------------------------------------
# SAVE LOGIC
if add_field or finish:

    new_data["field_number"] = field_idx
    new_data["producer_id"] = st.session_state.get("producer_id", "error")

    df = read_csv_from_dropbox_safely(field_FILE_PATH, list(new_data.keys()))
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)

    buf = StringIO()
    df.to_csv(buf, index=False)
    dbx.files_upload(
        buf.getvalue().encode(),
        field_FILE_PATH,
        mode=dropbox.files.WriteMode("overwrite")
    )

    if add_field:
        st.session_state.field_index += 1
        st.rerun()

    if finish:
        st.success("Submission complete. You may close the window.")