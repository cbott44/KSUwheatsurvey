#==================================================================================================================================
#Streamlit Setup
#==================================================================================================================================

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

#Define the color of form backgrounds + dark mode override
css = """
<style>
    /* Global override to force light mode */
    html, body, .stApp {
        background-color: white !important;
        color: black !important;
    }

    /* Info box override */
    .info-box {
        background-color: #f0f2f6 !important;
        color: black !important;
    }

    /* Form container */
    [data-testid="stForm"] {
        background: rgb(170,194,206) !important;
        color: black !important;
    }

    .stForm > div {
        margin-bottom: 0px;
    }

    .stMarkdown p {
        margin-bottom: 0px;
    }

    /* Expander header */
    div[data-testid="stExpander"] > details > summary {
        background-color: #e6e6e6 !important;
        color: black !important;
        border-radius: 0.5rem;
        padding: 0.5rem;
    }

    /* Expander content */
    div[data-testid="stExpander"] > details > div {
        background-color: #e6e6e6 !important;
        color: black !important;
        padding: 1rem;
        border-radius: 0 0 0.5rem 0.5rem;
    }

    /* Sidebar (optional) */
    section[data-testid="stSidebar"] {
        background-color: white !important;
        color: black !important;
    }

    /* Force input elements to appear light mode */
    input, textarea, select {
        background-color: white !important;
        color: black !important;
        border: 1px solid #ccc !important;
    }

    /* Fix text inputs and text areas inside Streamlit's widget container */
    div[data-baseweb="input"] input {
        background-color: white !important;
        color: black !important;
    }

    textarea {
        background-color: white !important;
        color: black !important;
    }

    /* Optional: remove Streamlit default focus ring */
    input:focus, textarea:focus, select:focus {
        outline: none !important;
        border: 1px solid #555 !important;
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
    new_data['ed_level'] = right.selectbox("Highest Level of Completed Education",options = ("--","less than highschool",
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
            <small style='color:gray;'>e.g. government 5 year flex plan, seasonally dry wells, etc.</small>
        </div>
        """, 
        unsafe_allow_html=True
    )

    new_data['limits'] = options_form.text_area("", height = 68)

    #agreement with the statements
    options_form.markdown("Rate the following two statements:")
    
    new_data['statement1'] = options_form.radio(
    "Managing water sustainably is essential for ensuring that agriculture remains viable in our region for future generations.",
    options=[
        "Select",
        "1 - Strongly Disagree",
        "2 - Disagree",
        "3 - Neutral",
        "4 - Agree",
        "5 - Strongly Agree"
            ]
        )

    new_data['statement2'] = options_form.radio(
    "Concerns about water availability significantly influence the crops I choose to plant and how I manage my fields.",
    options=[
        "Select",
        "1 - Strongly Disagree",
        "2 - Disagree",
        "3 - Neutral",
        "4 - Agree",
        "5 - Strongly Agree"
            ]
        )

    
    #submit buttons
    add_data = options_form.form_submit_button("Submit", type = "primary") #type controls the look
    clear_form = options_form.form_submit_button("Clear form", type = "secondary")
    
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
    st.write(df) 


#clear form instead of submitting
if clear_form:
    st.rerun()  # Reruns the script and resets everything

#============================================================================================================================================
#Form 2 - Field 1 Information
#nutrient inputs need examples
#============================================================================================================================================

#Make field1 disappear if adding another field
placeholder = st.empty()
if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False #start with field1 not submitted
if "form2_visible" not in st.session_state:
    st.session_state.form2_visible = False  #start with field2 not visible

#dictionary
new_data2 = {
    "producer_id":"",
    "yield": "",
    "yield_unit": "",
    "field_number": "",
    "lat": "",
    "long": "",
    "county_ident": "",
    "section": "",
    "township": "",
    "range": "",
    "irrigated": "",
    "crop_purpose": "",
    "prev_crop": "",
    "prev_crop_year": "",
    "prev_crop_irr": "",
    "field_size": "",
    "field_size_unit": "",
    "planting_date": "",
    "harvest_date": "",
    "forage_yield": "",
    "forage_unit": "",
    "impacting_events": "",
    "cultivar": "",
    "seed_treat": "",
    "seed_source": "",
    "seed_cleaned": "",
    "profile_h20":"",
    'K_soil':"",
    'P_soil':"",
    'N_soil':"",
    'N_soildepth':"",
    'row_space':"",
    'seeding_rate':"",
    'seeding_rate_unit':"",
    'furrow_fert_product':"",
    'furrow_fert_rate':"",
    'manure_freq':"",
    'manure_rate':"",
    'lime_time':"",
    'lime_rate':"",
    'lime_product':"",
    'P_time':"",
    'P_rate':"",
    'P_product':"",
    'K_time':"",
    'K_rate':"",
    'K_product':"",
    'N_time':"",
    'N_rate':"",
    'N_product':"",
    'micro_time':"",
    'micro_rate':"",
    'micro_product':"",
    'fungicide_freq':"",
    'fungicide_time':"",
    'insecticide_freq':"",
    'insecticide_time':"",
    'herbicide_freq':"",
    'herbicide_time':"",
    'irr_decision':"",
    'irr_type':"",
    'system_config':"",
    'system_capacity':"",
    'water_source':"",
    'capacity_flux':"",
    'pre_plant_water':"",
    'irr_number':"",
    'irr1_date':"",
    'irr1_stage':"",
    'irr1_amount':"",
    'irr1_rate':"",
    'irr1_fertigation':"",
    'irr2_date':"",
    'irr2_stage':"",
    'irr2_amount':"",
    'irr2_rate':"",
    'irr2_fertigation':"",
    'irr3_date':"",
    'irr3_stage':"",
    'irr3_amount':"",
    'irr3_rate':"",
    'irr3_fertigation':"",
    'irr4_date':"",
    'irr4_stage':"",
    'irr4_amount':"",
    'irr4_rate':"",
    'irr4_fertigation':"",
    'irr_shared':""
}


#read csv, populate fields if starting empty
columns = list(new_data2.keys())

df2 = read_csv_from_dropbox_safely(field_FILE_PATH, columns)
#-------------------------------------------------------------------------------------------------------------------------------------------------------
# show the form if field 1 hasn't been submitted    
if not st.session_state.form_submitted:
    with placeholder.form("field1 Form",clear_on_submit = False):
            st.markdown("### Field Specific Information")
            st.markdown("")
        
        #field location
            st.markdown("**Field Location:** *Provide ONE of the following 3 options*")
            
            st.markdown(
                "<small style='color:gray;'>Identify the specific field. Please be as precise as possible</small>",
                unsafe_allow_html=True
                 )

            with st.expander("Coordinates"):
                st.markdown("")
                st.markdown(
                    "<small style='color:black;'>If necessary, use Google Maps to locate the field and enter the coordinates here. </small>",
                    unsafe_allow_html=True
                     )
                st.link_button("Go to google maps", "https://www.google.com/maps/@39.1876134,-96.567296,2926m/data=!3m1!1e3?entry=ttu&g_ep=EgoyMDI1MDQyMS4wIKXMDSoASAFQAw%3D%3D")

                left, right = st.columns(2, vertical_alignment = "bottom")
                new_data2['lat'] = left.text_input("Latitude (*5+ decimal places*)")
                new_data2['long'] = right.text_input("Longitude")
           
            with st.expander("County and Rd Intersections"):
                st.markdown("")
            
                st.markdown(
                        "<small style='color:gray;'>ex: Riley CO, SW of Rd 11 & Sheridan</small>",
                        unsafe_allow_html=True
                         )
                new_data2['county_ident'] = st.text_input("County and Rd")
                
            
            with st.expander("Section/Township/Range"):
                st.markdown("")
    
                left, middle, right = st.columns(3, vertical_alignment = "bottom")
                new_data2['section'] = left.text_input("Section")
                new_data2['township'] = middle.text_input("Township")
                new_data2['range'] = right.text_input("Range")
        
            st.markdown("<hr>", unsafe_allow_html=True) 

        #------------------------------------------------------------------------------------------------#
            
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data2['field_size'] = left.text_input("Field Size")
            new_data2['field_size_unit'] = right.selectbox("Unit", options = ("Acres","Hectares"))
        
            #crop purpose, allow other
            crop_purpose = st.empty()
            placeholder_3 = st.empty() #input for other crop purpose

            #previous crop
            st.markdown("Previous Crop")
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data2['prev_crop'] = left.text_input("Previous Crop (ex: wheat)")
            new_data2['prev_crop_year'] = right.text_input("Harvest Year (ex: 2021)")

            new_data2['prev_crop_irr'] = st.radio("Did the previous crop receive irrigation?", options=("Select","yes", "no"), horizontal=True)
                        

        #------------------------------------------------------------------------------------------------#
            #soil testing
            with st.expander("**If Soil Testing Prior to Planting;** provide details here"):
                st.markdown("Upload Files **OR** Add Data Manually")
                st.markdown("")
                
                uploaded_files = st.file_uploader(
                    "Choose a file", accept_multiple_files=True
                )
            
                left, right = st.columns(2, vertical_alignment="bottom")
                new_data2['K_soil'] = left.text_input("Potassium (K) ppm")
                new_data2['P_soil'] = right.text_input("Phosphorus (P) ppm")
            
                left, right = st.columns(2, vertical_alignment="bottom")
                new_data2['N_soil'] = left.text_input("Nitrogen (Nitrate (NO3) ppm or N/acre)")
                new_data2['N_soildepth'] = right.text_input("N measured at what depth?")
            
            # Uploading to Dropbox
            if uploaded_files:
                number = 0
                producer_id = st.session_state.get("producer_id", None)
            
                if not producer_id:
                    st.warning("Producer ID is missing. Cannot save uploaded files.")
                else:
                    for uploaded_file in uploaded_files:
                        number += 1
            
                        # Extract file extension
                        file_extension = os.path.splitext(uploaded_file.name)[1]
            
                        # New filename format
                        new_filename = f"soiltest{number}_{producer_id}_field1{file_extension}"
                        dropbox_path = f"{soil_tests}/{new_filename}"
            
                        # Upload file to Dropbox
                        dbx.files_upload(
                            uploaded_file.read(),
                            dropbox_path,
                            mode=dropbox.files.WriteMode("overwrite")
                        )
                    
                    st.success(f"Uploaded {number} soil test file(s)")

        #------------------------------------------------------------------------------------------------#
            left, right = st.columns(2)
            new_data2['planting_date'] = left.date_input(
                "Planting Date",
                min_value=datetime.date(2000, 1, 1), #set farthest back date as 2000
                max_value=datetime.date.today())
            new_data2['harvest_date'] = right.date_input(
                "Harvest Date",
                min_value=datetime.date(2000, 1, 1),
                max_value=datetime.date.today())
           
            new_data2['cultivar'] = st.text_input("Cultivar Name (brand and number)")

            left,right = st.columns([2,1], vertical_alignment = "bottom")
            new_data2['seed_source'] = left.selectbox("Seed Source", options = ("--","Saved","Certified"))
            new_data2['seed_cleaned'] = right.selectbox("If saved seed, was it cleaned?", options = ("--","yes","no"))

            new_data2['seed_treat'] = st.selectbox("Seed Treatment?", options = ("--","None","Insecticide only","Fungicide only","Both"))

            new_data2['profile_h20'] = st.text_input("Estimated profile water at planting (ft)")

        
            new_data2['row_space'] = st.text_input("Row Spacing (inches)")
            
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data2['seeding_rate'] = left.text_input("Seeding Rate")
            new_data2['seeding_rate_unit'] = right.selectbox("Seeding Rate Units", options = ("lbs/ac","seeds/ac"))
            

            st.markdown("<hr>", unsafe_allow_html=True)
            #side by side yield and units
            left,right = st.columns([2,1], vertical_alignment = "bottom")
            new_data2['yield'] = left.text_input("Grain Yield")
            yield_unit = right.empty()
            placeholder_text = st.empty() #input options for other units
  
            left,right = st.columns([2,1], vertical_alignment = "bottom")
            new_data2['forage_yield'] = left.text_input("Forage Yield if Applicable")
            new_data2['forage_unit'] = right.text_input("Yield Unit")

            st.markdown("Describe any events that may have significantly impacted yield")
            st.markdown(
                "<small style='color:gray;'>e.g. Stripe rust impacted 20% of field</small>",
                unsafe_allow_html=True
                 )
            new_data2['impacting_events'] = st.text_area("", height = 68)

       #------------------------------------------------------------------------------------------------#
            st.markdown("<hr>", unsafe_allow_html=True)  #line
            st.markdown("**Inputs**")
            
            #Inputs
            #furrow fertilizer
            st.markdown(
            "<small style='color:black;'>In-Furrow Fertilizer? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data2['furrow_fert_product'] = right.text_input("Product (*ex:18-46-00 DAP*)")
            new_data2['furrow_fert_rate'] = left.text_input("Rate (*ex: 30 lbs/ac*)")
            
            #manure
            st.markdown(
            "<small style='color:black;'>Manure Use? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data2['manure_freq'] = right.text_input("Frequency (*every other year*)")
            new_data2['manure_rate'] = left.text_input("Rate (*ex:30t/ac*)")

            #lime
            st.markdown(
            "<small style='color:black;'>Lime? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, middle, right = st.columns(3, vertical_alignment = "bottom")
            new_data2['lime_time'] = left.text_input("time of applications (*early sept*)")
            new_data2['lime_rate'] = middle.text_input("Rate (*ex:5000 lb/ac*)")
            new_data2['lime_product'] = right.text_input("Product (*ex:ECC*)")

            #Phosphorus
            st.markdown(
            "<small style='color:black;'>Phosphorus (P)? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, middle, right = st.columns(3, vertical_alignment = "bottom")
            new_data2['P_time'] = left.text_input("time of applications (*planting*)")
            new_data2['P_rate'] = middle.text_input("Rate (*ex:*)")
            new_data2['P_product'] = right.text_input("Product (*ex:*)")

            #Potassium
            st.markdown(
            "<small style='color:black;'>Potassium (K)? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, middle, right = st.columns(3, vertical_alignment = "bottom")
            new_data2['K_time'] = left.text_input("time of applications (*fill*)")
            new_data2['K_rate'] = middle.text_input("Rate (*fill*)")
            new_data2['K_product'] = right.text_input("Product (*fill*)")

            #Nitrogen
            st.markdown(
            "<small style='color:black;'>Nitrogen (N)? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, middle, right = st.columns(3, vertical_alignment = "bottom")
            new_data2['N_time'] = left.text_input("time of applications (*top dress at greenup*)")
            new_data2['N_rate'] = middle.text_input("Rate (*ex:60 lb/ac*)")
            new_data2['N_product'] = right.text_input("Product (*ex: UAN*)")

            #Micronutrients
            st.markdown(
            "<small style='color:black;'>Micronutrients? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, middle, right = st.columns(3, vertical_alignment = "bottom")
            new_data2['micro_time'] = left.text_input("time of applications")
            new_data2['micro_rate'] = middle.text_input("Rate")
            new_data2['micro_product'] = right.text_input("Product")
        

            st.markdown(
            "<small style='color:black;'>Fungicide Use? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data2['fungicide_freq'] = right.text_input("Number of Applications")
            new_data2['fungicide_time'] = left.text_input("Time of Applications (*ex: boot stage*)")

            st.markdown(
            "<small style='color:black;'>Insecticide Use? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data2['insecticide_freq'] = right.text_input("Number of Applications ")
            new_data2['insecticide_time'] = left.text_input("Time of Applications")

            st.markdown(
            "<small style='color:black;'>Herbicide Use? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data2['herbicide_freq'] = right.text_input("Number of Applications  ")
            new_data2['herbicide_time'] = left.text_input("Time of Applications (*ex: pre-harvest*)")

                #------------------------------------------------------------------------------------------------#
            #Irrigation    
            new_data2['irrigated'] = st.radio("**Did this wheat crop receive irrigation?**", options=("Select","yes", "no"), horizontal=True)
 
            st.markdown("<hr>", unsafe_allow_html=True) 
            st.markdown("**Irrigation Management**")
            st.markdown(
            "<small style='color:gray;'>Complete the following questions if this field recieved irrigation</small>",
            unsafe_allow_html=True
             )
            st.markdown("")
            new_data2['irr_shared']= st.text_input("Is the reported water supply shared with another crop? (*ex: half pivot was corn*)")
            new_data2['irr_decision'] = st.text_area("What drives your decision to trigger an irrigation event? (*ex: visual appearance of soil, moisture sensor*)", height = 68)
            new_data2['irr_type'] = st.text_input("Irrigation Method (*i.e. center pivot, flood*)") 
            new_data2['system_config'] = st.text_area("Briefly describe the sprinkler configuration: spacing, height...", height = 68)
            
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data2['system_capacity'] = left.text_input("System Capacity (*gal/min*)")
            new_data2['water_source'] = right.text_input("Water source (*i.e. ground, surface*)")
        
            new_data2['capacity_flux'] = st.text_input("Does system capacity fluctuate throughout the season (*if yes, breifly explain*)")
            new_data2['pre_plant_water'] = st.radio("Pre-plant water applied?", options = ("Select","yes","no"), horizontal=True)
            new_data2['irr_number'] = st.text_input("Number of irrigation events throughout the season (*including pre-plant*)")

        #irrigation event 1
            st.markdown("") 
            st.markdown("**Provide Information About Each Irrigation Event**")
    
            with st.expander("First Application (or pre-plant)"):
                new_data2['irr1_date'] =st.date_input("Irrigation Date", 
                                                    min_value=datetime.date(2000, 1, 1),
                                                    max_value=datetime.date.today(),
                                                    key = 'irr1_date')  #use key to get around having identical widgets
                new_data2['irr1_stage'] =st.text_input("Crop Stage at time of Irrigation", key ='irr1_stage' )
                
                left, right = st.columns(2,vertical_alignment = "bottom")
                new_data2['irr1_amount'] =left.text_input("Amount of water applied (*gals*)", key ='irr1_amount' )
                new_data2['irr1_rate'] =right.text_input("Rate of application (*gal/min*)", key = 'irr1_rate')
                new_data2['irr1_fertigation'] = st.radio("Fertigation?", options = ("Select","yes","no"), horizontal=True, key = 'irr1_fertigation')

            with st.expander("Second Application"):
                new_data2['irr2_date'] =st.date_input("Irrigation Date",
                                                    min_value=datetime.date(2000, 1, 1),
                                                    max_value=datetime.date.today(), 
                                                    key = 'irr2_date')
                new_data2['irr2_stage'] =st.text_input("Crop Stage at time of Irrigation",key ='irr2_stage' )
                
                left, right = st.columns(2,vertical_alignment = "bottom")
                new_data2['irr2_amount'] =left.text_input("Amount of water applied (*gals*)", key ='irr2_amount' )
                new_data2['irr2_rate'] =right.text_input("Rate of application (*gal/min*)", key = 'irr2_rate')
                new_data2['irr2_fertigation'] = st.radio("Fertigation?", options = ("Select","yes","no"), horizontal=True, key = 'irr2_fertigation')

            with st.expander("Third Application"):
                new_data2['irr3_date'] =st.date_input("Irrigation Date",min_value=datetime.date(2000, 1, 1),max_value=datetime.date.today(), key = 'irr3_date')
                new_data2['irr3_stage'] =st.text_input("Crop Stage at time of Irrigation", key ='irr3_stage' )
                
                left, right = st.columns(2,vertical_alignment = "bottom")
                new_data2['irr3_amount'] =left.text_input("Amount of water applied (*gals*)", key ='irr3_amount' )
                new_data2['irr3_rate'] =right.text_input("Rate of application (*gal/min*)", key = 'irr3_rate')
                new_data2['irr3_fertigation'] = st.radio("Fertigation?", options = ("Select","yes","no"), horizontal=True, key = 'irr3_fertigation')

            with st.expander("Fourth Application"):
                new_data2['irr4_date'] =st.date_input("Irrigation Date", min_value=datetime.date(2000, 1, 1),max_value=datetime.date.today(),key = 'irr4_date')
                new_data2['irr4_stage'] =st.text_input("Crop Stage at time of Irrigation", key ='irr4_stage' )
                
                left, right = st.columns(2,vertical_alignment = "bottom")
                new_data2['irr4_amount'] =left.text_input("Amount of water applied (*gals*)", key ='irr4_amount' )
                new_data2['irr4_rate'] =right.text_input("Rate of application (*gal/min*)", key = 'irr4_rate')
                new_data2['irr4_fertigation'] = st.radio("Fertigation?", options = ("Select","yes","no"), horizontal=True, key = 'irr4_fertigation')

        
            #submit buttons
            dd_data = st.form_submit_button("Add another field", type = "primary") #type controls the look
            finish = st.form_submit_button("Finish", type = "secondary")
        
            if finish:
                st.markdown(
                    """
                    <div style='background-color: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 20px;'>
                        <strong style='color: green;'> Submission Successful:</strong> You may close the window
                    </div>
                    """,
                    unsafe_allow_html=True
                )
     #------------------------------------------------------------------------------------------------#
#define other crop purpose
    with crop_purpose:
        selection3 = st.selectbox("Primary Purpose of Wheat Crop", options = ("--","seed","grain","forage","dual-purpose","other"), key ='other1')
    with placeholder_3:
        if selection3 == "other":
            crop_purpose_other = st.text_input("Enter other purpose", key = 'other2')


#define other yield units
    with yield_unit:
        selection = st.selectbox("Yield Unit",options = ("bu/ac","t/ha","lb/ac","kg/ha","other"), key = 'unit1')
    with placeholder_text:
        if selection == "other":
            otherOption = st.text_input("Enter other units", key = 'unit2')

    #------------------------------------------------------------------------------------------------#
#add data       
    if dd_data:
            st.session_state.form_submitted = True #field1 disapears
            st.session_state.form2_visible = True #field2 becomes visible
        
            new_data2['field_number'] = 1 #always is the first submission
        
            producer_id = st.session_state.get('producer_id', None) #take from where ID is created in form 1 and saved in session state
            if producer_id is None:
                    new_data2['producer_id'] = "error"
            else:
                # include producer_id when saving field info
                new_data2['producer_id'] = producer_id 
                
        #other yield units
            units_temp = ""
            if selection == "other":
                units_temp = otherOption
            else:
                units_temp = selection
    
            new_data2['yield_unit'] = units_temp
        
        #other crop purpose 
            purpose_temp = ""
            if selection3 == "other":
                purpose_temp = crop_purpose_other
            else:
                purpose_temp = selection3
    
            new_data2['crop_purpose'] = purpose_temp
    
            #add to csv
                        
            df2 = read_csv_from_dropbox_safely(field_FILE_PATH, columns)
        
            df2 = df2.loc[:, ~df2.columns.str.contains('^Unnamed')]  #to correct problems with unnamed columns
        
            new_df2 = pd.DataFrame([new_data2]) #dictionary to data frame

            df2 = pd.concat([df2, new_df2], ignore_index=True) 
                     
            # Save updated DataFrame to Dropbox
            csv_buffer2 = StringIO()
            df2.to_csv(csv_buffer2, index=False)
            dbx.files_upload(csv_buffer2.getvalue().encode(), field_FILE_PATH, mode=dropbox.files.WriteMode("overwrite"))

            placeholder.empty()  
            st.rerun() 
            #Display updated file
            st.write(df2) 

#finish       
    if finish:
            new_data2['field_number'] = 1   

            #capture producer ID from form 1
            producer_id = st.session_state.get('producer_id', None)
            if producer_id is None:
                    new_data2['producer_id'] = "error"
            else:
                # include producer_id when saving field info
                new_data2['producer_id'] = producer_id
                
            #other yield units
            units_temp = ""
            if selection == "other":
                units_temp = otherOption
            else:
                units_temp = selection
    
            new_data2['yield_unit'] = units_temp
        
            #other crop purpose 
            purpose_temp = ""
            if selection3 == "other":
                purpose_temp = crop_purpose_other
            else:
                purpose_temp = selection3
    
            new_data2['crop_purpose'] = purpose_temp
    
            #add to csv  
            df2 = read_csv_from_dropbox_safely(field_FILE_PATH, columns)
            df2 = df2.loc[:, ~df2.columns.str.contains('^Unnamed')]
        
            new_df2 = pd.DataFrame([new_data2]) #dictionary to data frame

            df2 = pd.concat([df2, new_df2], ignore_index=True) 
                    
            # Save updated DataFrame to Dropbox
            csv_buffer2 = StringIO()
            df2.to_csv(csv_buffer2, index=False)
            dbx.files_upload(csv_buffer2.getvalue().encode(), field_FILE_PATH, mode=dropbox.files.WriteMode("overwrite"))
            
            st.write(df2)


#=====================================================================================================================================================
#Form 3 - Additional fields
#=====================================================================================================================================================

        
new_data3 = {
    "producer_id":"",
    "yield": "",
    "yield_unit": "",
    "field_number": "",
    "lat": "",
    "long": "",
    "county_ident": "",
    "section": "",
    "township": "",
    "range": "",
    "irrigated": "",
    "crop_purpose": "",
    "prev_crop": "",
    "prev_crop_year": "",
    "prev_crop_irr": "",
    "field_size": "",
    "field_size_unit": "",
    "planting_date": "",
    "harvest_date": "",
    "forage_yield": "",
    "forage_unit": "",
    "impacting_events": "",
    "cultivar": "",
    "seed_treat": "",
    "seed_source": "",
    "seed_cleaned": "",
    "profile_h20":"",
    'K_soil':"",
    'P_soil':"",
    'N_soil':"",
    'N_soildepth':"",
    'row_space':"",
    'seeding_rate':"",
    'seeding_rate_unit':"",
    'furrow_fert_product':"",
    'furrow_fert_rate':"",
    'manure_freq':"",
    'manure_rate':"",
    'lime_time':"",
    'lime_rate':"",
    'lime_product':"",
    'P_time':"",
    'P_rate':"",
    'P_product':"",
    'K_time':"",
    'K_rate':"",
    'K_product':"",
    'N_time':"",
    'N_rate':"",
    'N_product':"",
    'micro_time':"",
    'micro_rate':"",
    'micro_product':"",
    'fungicide_freq':"",
    'fungicide_time':"",
    'insecticide_freq':"",
    'insecticide_time':"",
    'herbicide_freq':"",
    'herbicide_time':"",
    'irr_decision':"",
    'irr_type':"",
    'system_config':"",
    'system_capacity':"",
    'water_source':"",
    'capacity_flux':"",
    'pre_plant_water':"",
    'irr_number':"",
    'irr1_date':"",
    'irr1_stage':"",
    'irr1_amount':"",
    'irr1_rate':"",
    'irr1_fertigation':"",
    'irr2_date':"",
    'irr2_stage':"",
    'irr2_amount':"",
    'irr2_rate':"",
    'irr2_fertigation':"",
    'irr3_date':"",
    'irr3_stage':"",
    'irr3_amount':"",
    'irr3_rate':"",
    'irr3_fertigation':"",
    'irr4_date':"",
    'irr4_stage':"",
    'irr4_amount':"",
    'irr4_rate':"",
    'irr4_fertigation':"",
    'irr_shared':""
}

#---------------------------------------------------------------------------------------------------------------------------------------
if st.session_state.form2_visible:
    with st.form("Another Field",clear_on_submit = True):
            st.markdown("### Field Specific Information")
            st.markdown("**Add Another Field**", unsafe_allow_html=True)
            st.markdown("")
        
            #field location
            st.markdown("**Field Location:** *Provide ONE of the following 3 options*")
            
            st.markdown(
                "<small style='color:gray;'>Identify the specific field. Please be as precise as possible</small>",
                unsafe_allow_html=True
                 )

            with st.expander("Coordinates"):
                st.markdown("")
                st.markdown(
                    "<small style='color:black;'>If necessary, use Google Maps to locate the field and enter the coordinates here. </small>",
                    unsafe_allow_html=True
                     )
                st.link_button("Go to google maps", "https://www.google.com/maps/@39.1876134,-96.567296,2926m/data=!3m1!1e3?entry=ttu&g_ep=EgoyMDI1MDQyMS4wIKXMDSoASAFQAw%3D%3D")

                left, right = st.columns(2, vertical_alignment = "bottom")
                new_data3['lat'] = left.text_input("Latitude", key = 'lat2')
                new_data3['long'] = right.text_input("Longitude", key = 'long2')
           
            with st.expander("County and Rd Intersections"):
                st.markdown("")
            
                st.markdown(
                        "<small style='color:gray;'>ex: Riley CO, SW of Rd 11 & Sheridan</small>",
                        unsafe_allow_html=True
                         )
                new_data3['county_ident'] = st.text_input("County and Rd", key = 'county2')
                
            
            with st.expander("Section/Township/Range"):
                st.markdown("")
    
                left, middle, right = st.columns(3, vertical_alignment = "bottom")
                new_data3['section'] = left.text_input("Section", key ='section2')
                new_data3['township'] = middle.text_input("Township", key ='twnsp2')
                new_data3['range'] = right.text_input("Range", key = 'range2')
        
            st.markdown("<hr>", unsafe_allow_html=True) 

        #------------------------------------------------------------------------------------------------#
            
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data3['field_size'] = left.text_input("Field Size", key = 'size2')
            new_data3['field_size_unit'] = right.selectbox("Unit", options = ("Acres","Hectares"), key = 'sizeunit2')
        
            #crop purpose
            crop_purpose = st.empty()
            placeholder_3 = st.empty() #input for other crop purpose

            #previous crop
            st.markdown("Previous Crop")
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data3['prev_crop'] = left.text_input("Previous Crop (ex: wheat)",key = 'prevcrop2')
            new_data3['prev_crop_year'] = right.text_input("Harvest Year (ex: 2021)", key = 'prevcropyear2')

            new_data3['prev_crop_irr'] = st.radio("Did the previous crop receive irrigation?", options=("Select","yes", "no"), 
                                                  horizontal=True, key = 'previrr2')
                        

        #------------------------------------------------------------------------------------------------#
            #soil testing

            with st.expander("**If Soil Testing Prior to Planting;** provide details here"):
                st.markdown("Upload Files **OR** Add Data Manually")
                st.markdown("")
            
                uploaded_files = st.file_uploader(
                    "Choose a file", accept_multiple_files=True, key='upload2'
                )
            
                left, right = st.columns(2, vertical_alignment="bottom")
                new_data3['K_soil'] = left.text_input("Potassium (K) ppm", key='k2')
                new_data3['P_soil'] = right.text_input("Phosphorus (P) ppm", key='p2')
            
                left, right = st.columns(2, vertical_alignment="bottom")
                new_data3['N_soil'] = left.text_input("Nitrogen (Nitrate (NO3) ppm or N/acre)", key='n2')
                new_data3['N_soildepth'] = right.text_input("N measured at what depth?", key='ndepth2')
            
            # Handle uploads
            if uploaded_files:
                number = 0
            
                # Safely read fields_info.csv from Dropbox
                df2 = read_csv_from_dropbox_safely(field_FILE_PATH, list(new_data3.keys()))
                
                # Determine next field number
                if not df2.empty and 'field_number' in df2.columns:
                    last_field_numbertemp = df2['field_number'].iloc[-1]
                else:
                    last_field_numbertemp = 0
            
                field_numbtemp = int(last_field_numbertemp) + 1
            
                producer_id2 = st.session_state.get("producer_id", None)
                if producer_id2 is None:
                    st.warning("Producer ID not found in session state.")
                else:
                    for uploaded_file in uploaded_files:
                        number += 1
                        file_extension = os.path.splitext(uploaded_file.name)[1]
                        new_filename = f"soiltest{number}_{producer_id2}_field{field_numbtemp}{file_extension}"
            
                        # Define Dropbox path
                        dropbox_path = f"/streamlit/soiltest_uploads/{new_filename}"
            
                        # Upload file to Dropbox
                        dbx.files_upload(
                            uploaded_file.read(),
                            dropbox_path,
                            mode=dropbox.files.WriteMode("overwrite")
                        )
            
                    st.success(f"Uploaded soil test file(s)")
        #------------------------------------------------------------------------------------------------#

            left, right = st.columns(2)
            new_data3['planting_date'] = left.date_input("Planting Date",
                min_value=datetime.date(2000, 1, 1),
                max_value=datetime.date.today(), key = 'pd2')
            new_data3['harvest_date'] = right.date_input("Harvest Date",
                min_value=datetime.date(2000, 1, 1),
                max_value=datetime.date.today(), key = 'hd2')
           
            new_data3['cultivar'] = st.text_input("Cultivar Name (brand and number)", key = 'cultivar2')

            left,right = st.columns([2,1], vertical_alignment = "bottom")
            new_data3['seed_source'] = left.selectbox("Seed Source", options = ("--","Saved","Certified"), key = 'seedsource2')
            new_data3['seed_cleaned'] = right.selectbox("If saved seed, was it cleaned?", options = ("--","yes","no"), key = 'seedclean2')

            new_data3['seed_treat'] = st.selectbox("Seed Treatment?", options = ("--","None","Insecticide only","Fungicide only","Both"), key = 'seedtreat2')

            new_data3['profile_h20'] = st.text_input("Estimated profile water at planting (ft)", key = 'profile2')

        
            new_data3['row_space'] = st.text_input("Row Spacing (inches)", key = 'rowspace2')
            
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data3['seeding_rate'] = left.text_input("Seeding Rate", key = 'seedingrate2')
            new_data3['seeding_rate_unit'] = right.selectbox("Seeding Rate Units", options = ("lbs/ac","seeds/ac"), key = 'rateunit2')
            

            st.markdown("<hr>", unsafe_allow_html=True)
            #side by side yield and units
            left,right = st.columns([2,1], vertical_alignment = "bottom")
            new_data3['yield'] = left.text_input("Grain Yield", key = 'yield2')
            yield_unit = right.empty()
            placeholder_text = st.empty() #input options for other units
  
            left,right = st.columns([2,1], vertical_alignment = "bottom")
            new_data3['forage_yield'] = left.text_input("Forage Yield if Applicable", key = 'forage2')
            new_data3['forage_unit'] = right.text_input("Yield Unit", key = 'forageunit2')

            st.markdown("Describe any events that may have significantly impacted yield")
            st.markdown(
                "<small style='color:gray;'>e.g. Stripe rust impacted 20% of field</small>",
                unsafe_allow_html=True
                 )
            new_data3['impacting_events'] = st.text_input("", key = 'impacting2')

       #------------------------------------------------------------------------------------------------#
            st.markdown("<hr>", unsafe_allow_html=True) 
            st.markdown("**Inputs**")
            
            #Inputs
            #furrow fertilizer
            st.markdown(
            "<small style='color:black;'>In-Furrow Fertilizer? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data3['furrow_fert_product'] = right.text_input("Product (*ex:18-46-00 DAP*)", key = 'furrow2')
            new_data3['furrow_fert_rate'] = left.text_input("Rate (*ex: 30 t/ac*)", key = 'furrowrate2')
            
            #manure
            st.markdown(
            "<small style='color:black;'>Manure Use? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data3['manure_freq'] = right.text_input("Frequency (*every other year*)", key = 'manure2')
            new_data3['manure_rate'] = left.text_input("Rate (*ex:30t/ac*)", key = 'manurerate2')

            #lime
            st.markdown(
            "<small style='color:black;'>Lime? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, middle, right = st.columns(3, vertical_alignment = "bottom")
            new_data3['lime_time'] = left.text_input("time of applications (*early sept*)", key = 'limetime2')
            new_data3['lime_rate'] = middle.text_input("Rate (*ex:5000 lb/ac*)", key = 'limerate2')
            new_data3['lime_product'] = right.text_input("Product (*ex:ECC*)", key = 'limeproduct2')

            #Phosphorus
            st.markdown(
            "<small style='color:black;'>Phosphorus (P)? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, middle, right = st.columns(3, vertical_alignment = "bottom")
            new_data3['P_time'] = left.text_input("time of applications (*planting*)", key = 'ptime2')
            new_data3['P_rate'] = middle.text_input("Rate (*ex:*)", key = 'prate2')
            new_data3['P_product'] = right.text_input("Product (*ex:*)", key = 'pprod2')

            #Potassium
            st.markdown(
            "<small style='color:black;'>Potassium (K)? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, middle, right = st.columns(3, vertical_alignment = "bottom")
            new_data3['K_time'] = left.text_input("time of applications (*fill*)", key = 'ktime2')
            new_data3['K_rate'] = middle.text_input("Rate (*fill*)", key = 'krate2')
            new_data3['K_product'] = right.text_input("Product (*fill*)", key = 'kprod2')

            #Nitrogen
            st.markdown(
            "<small style='color:black;'>Nitrogen (N)? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, middle, right = st.columns(3, vertical_alignment = "bottom")
            new_data3['N_time'] = left.text_input("time of applications (*top dress at greenup*)", key = 'ntime2')
            new_data3['N_rate'] = middle.text_input("Rate (*ex:60 lb/ac*)", key = 'nrate2')
            new_data3['N_product'] = right.text_input("Product (*ex: UAN*)", key = 'nprod2')

            #Micronutrients
            st.markdown(
            "<small style='color:black;'>Micronutrients? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, middle, right = st.columns(3, vertical_alignment = "bottom")
            new_data3['micro_time'] = left.text_input("time of applications", key = 'microtime2')
            new_data3['micro_rate'] = middle.text_input("Rate", key ='microrate2')
            new_data3['micro_product'] = right.text_input("Product", key ='mircoprod2')
        

            st.markdown(
            "<small style='color:black;'>Fungicide Use? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data3['fungicide_freq'] = right.text_input("Number of Applications", key ='fungfreq2')
            new_data3['fungicide_time'] = left.text_input("Time of Applications (*ex: boot stage*)", key = 'fungtime2')

            st.markdown(
            "<small style='color:black;'>Insecticide Use? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data3['insecticide_freq'] = right.text_input("Number of Applications ", key ='insect2')
            new_data3['insecticide_time'] = left.text_input("Time of Applications", key = 'insecttime2')

            st.markdown(
            "<small style='color:black;'>Herbicide Use? (if yes...)</small>",
            unsafe_allow_html=True
             )
        
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data3['herbicide_freq'] = right.text_input("Number of Applications  ",  key ='herbfreq2')
            new_data3['herbicide_time'] = left.text_input("Time of Applications (*ex: pre-harvest*)",  key ='herbtime2')

                #------------------------------------------------------------------------------------------------#
            #Irrigation    
            new_data2['irrigated'] = st.radio("Did this wheat crop receive irrigation?", options=("Select","yes", "no"), horizontal=True)
 
            st.markdown("<hr>", unsafe_allow_html=True) 
            st.markdown("**Irrigation Management**")
            st.markdown(
            "<small style='color:gray;'>Complete the following questions if this field recieved irrigation</small>",
            unsafe_allow_html=True
             )
            st.markdown("")
            new_data3['irr_shared']= st.text_input("Is the reported water supply shared with another crop? (*ex: half pivot was corn*)", key = 'irrshare2')
            new_data3['irr_decision'] = st.text_area("What drives your decision to trigger an irrigation event? (*ex: visual appearance of soil, moisture sensor*)", height = 68, key = 'irrdescision2')
            new_data3['irr_type'] = st.text_input("Irrigation Method (*i.e. center pivot, flood*)", key = 'irrtype2') 
            new_data3['system_config'] = st.text_area("Briefly describe the sprinkler configuration: spacing, height...", height = 68, key = 'system2')
            
            left, right = st.columns(2, vertical_alignment = "bottom")
            new_data3['system_capacity'] = left.text_input("System Capacity (*gal/min*)", key = 'systemcapac2')
            new_data3['water_source'] = right.text_input("Water source (*i.e. ground, surface*)", key = 'source2')
        
            new_data3['capacity_flux'] = st.text_input("Does system capacity fluctuate throughout the season (*if yes, breifly explain*)", key = 'capacflux2')
            new_data3['pre_plant_water'] = st.radio("Pre-plant water applied?", options = ("Select","yes","no"), horizontal=True, key = 'preplant2')
            new_data3['irr_number'] = st.text_input("Number of irrigation events throughout the season (*including pre-plant*)", key = 'irrnumb2')

            #irrigation event 1
            st.markdown("") 
            st.markdown("**Provide Information About Each Irrigation Event**")

            with st.expander("First Application (or pre-plant) form2 "):
                new_data3['irr1_date'] =st.date_input("Irrigation Date", key = 'irr1_date2')  #use key to get around having identical widgets
                new_data3['irr1_stage'] =st.text_input("Crop Stage at time of Irrigation", key ='irr1_stage2' )
                
                left, right = st.columns(2,vertical_alignment = "bottom")
                new_data3['irr1_amount'] =left.text_input("Amount of water applied (*gals*)", key ='irr1_amount2' )
                new_data3['irr1_rate'] =right.text_input("Rate of application (*gal/min*)", key = 'irr1_rate2')
                new_data3['irr1_fertigation'] = st.radio("Fertigation?", options = ("Select","yes","no"), horizontal=True, key = 'irr1_fertigation2')

            with st.expander("Second Application  "):
                new_data3['irr2_date'] =st.date_input("Irrigation Date", key = 'irr2_date2')
                new_data3['irr2_stage'] =st.text_input("Crop Stage at time of Irrigation", key ='irr2_stage2' )
                
                left, right = st.columns(2,vertical_alignment = "bottom")
                new_data3['irr2_amount'] =left.text_input("Amount of water applied (*gals*)", key ='irr2_amount2' )
                new_data3['irr2_rate'] =right.text_input("Rate of application (*gal/min*)", key = 'irr2_rate2')
                new_data3['irr2_fertigation'] = st.radio("Fertigation?", options = ("Select","yes","no"), horizontal=True, key = 'irr2_fertigation2')

            with st.expander("Third Application  "):
                new_data3['irr3_date'] =st.date_input("Irrigation Date", key = 'irr3_date2')
                new_data3['irr3_stage'] =st.text_input("Crop Stage at time of Irrigation", key ='irr3_stage2' )
                
                left, right = st.columns(2,vertical_alignment = "bottom")
                new_data3['irr3_amount'] =left.text_input("Amount of water applied (*gals*)", key ='irr3_amount2' )
                new_data3['irr3_rate'] =right.text_input("Rate of application (*gal/min*)", key = 'irr3_rate2')
                new_data3['irr3_fertigation'] = st.radio("Fertigation?", options = ("Select","yes","no"), horizontal=True, key = 'irr3_fertigation2')

            with st.expander("Fourth Application  "):
                new_data3['irr4_date'] =st.date_input("Irrigation Date", key = 'irr4_date2')
                new_data3['irr4_stage'] =st.text_input("Crop Stage at time of Irrigation", key ='irr4_stage2' )
                
                left, right = st.columns(2,vertical_alignment = "bottom")
                new_data3['irr4_amount'] =left.text_input("Amount of water applied (*gals*)", key ='irr4_amount2' )
                new_data3['irr4_rate'] =right.text_input("Rate of application (*gal/min*)", key = 'irr4_rate2')
                new_data3['irr4_fertigation'] = st.radio("Fertigation?", options = ("Select","yes","no"), horizontal=True, key = 'irr4_fertigation2')

              #submit buttons
            submit2 = st.form_submit_button("Add another field", type = "primary") #type controls the look
            finish2 = st.form_submit_button("Finish", type = "secondary")

        
            if finish2:
                st.markdown(
                    """
                    <div style='background-color: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 20px;'>
                        <strong style='color: green;'> Submission Successful:</strong> You may close the window
                    </div>
                    """,
                    unsafe_allow_html=True
                )
#---------------------------------------------------------------------------------------
#define other crop purpose
    with crop_purpose:
        selection3 = st.selectbox("Primary Purpose of Wheat Crop", options = ("--","seed","grain","forage","dual-purpose","other"), key = 'select3')
    with placeholder_3:
        if selection3 == "other":
            crop_purpose_other = st.text_input("Enter other purpose", key = 'purp3')


#define other yield units
    with yield_unit:
        selection2 = st.selectbox("Yield Unit",options = ("bu/ac","t/ha","lb/ac","kg/ha","other"), key = 'selection3')
    with placeholder_text:
        if selection2 == "other":
            otherOption2 = st.text_input("Enter other units", key = 'other2')
#----------------------------------------------------------------------------------------          

#add data       
    if submit2:
        #grab last field number from above csv line and add 1
            df2 = read_csv_from_dropbox_safely(field_FILE_PATH, columns) #need to call it here
            df2 = df2.loc[:, ~df2.columns.str.contains('^Unnamed')] #remove filler columns
            last_field_number = df2['field_number'].iloc[-1] if not df2.empty else 0
            new_data3['field_number'] = last_field_number + 1
        
        #producer ID from session state
            producer_id = st.session_state.get('producer_id', None)
            if producer_id is None:
                    new_data3['producer_id'] = "error"
            else:
                # include producer_id when saving field info
                new_data3['producer_id'] = producer_id
                
        #other yield units
            units_temp = ""
            if selection2 == "other":
                units_temp2 = otherOption2
            else:
                units_temp2 = selection2
    
            new_data3['yield_unit'] = units_temp2
        
        #other crop purpose 
            purpose_temp = ""
            if selection3 == "other":
                purpose_temp2 = crop_purpose_other
            else:
                purpose_temp2 = selection3
    
            new_data3['crop_purpose'] = purpose_temp2
    
            #add to csv
            
            new_df3 = pd.DataFrame([new_data3]) #dictionary to data frame

            df2 = pd.concat([df2, new_df3], ignore_index=True) 
            
            # Save updated DataFrame to Dropbox
            csv_buffer2 = StringIO()
            df2.to_csv(csv_buffer2, index=False)
            dbx.files_upload(csv_buffer2.getvalue().encode(), field_FILE_PATH, mode=dropbox.files.WriteMode("overwrite"))

            placeholder.empty()  
            st.rerun() 
            #Display updated file
            st.write(df2) 

#finish       
    if finish2:
            #grab last field number and add 1
            df2 = read_csv_from_dropbox_safely(field_FILE_PATH, columns)
            df2 = df2.loc[:, ~df2.columns.str.contains('^Unnamed')]
                
            last_field_number = df2['field_number'].iloc[-1] if not df2.empty else 0
            new_data3['field_number'] = last_field_number + 1
        #producer ID from session state
            producer_id = st.session_state.get('producer_id', None)
            if producer_id is None:
                    new_data3['producer_id'] = "error"
            else:
                # include producer_id when saving field info
                new_data3['producer_id'] = producer_id
                
        #other yield units
            units_temp = ""
            if selection2 == "other":
                units_temp2 = otherOption2
            else:
                units_temp2 = selection2
    
            new_data3['yield_unit'] = units_temp2
        
        #other crop purpose 
            purpose_temp = ""
            if selection3 == "other":
                purpose_temp2 = crop_purpose_other
            else:
                purpose_temp2 = selection3
    
            new_data3['crop_purpose'] = purpose_temp2
    
            #add to csv
            new_df3 = pd.DataFrame([new_data3]) #dictionary to data frame

            df2 = pd.concat([df2, new_df3], ignore_index=True) 
            
            # Save updated DataFrame to Dropbox
            csv_buffer2 = StringIO()
            df2.to_csv(csv_buffer2, index=False)
            dbx.files_upload(csv_buffer2.getvalue().encode(), field_FILE_PATH, mode=dropbox.files.WriteMode("overwrite"))

            placeholder.empty()  
            #st.rerun() 
        
            #Display updated file
            st.write(df2) 




