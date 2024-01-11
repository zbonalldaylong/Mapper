# Plotly Mapper

Script to output a customized world map that combines Plotly/Mapbox base map with user-specified data and features (geojson, eg). 

## Notes
* Style, setting, and content attributes input by user before execution.  
* MapBuilder class checks for custom features on inititialization in features sub-directory; named feature_1.geojson, feature_2.geojson, etc. 
* MapBuilder class downloads and unzips geographic data for populated places based on user-specified country (self.content['country_list']) on initialization. 
* Sub-national borders (provinces, states) can be initialized via a settings toggle.
* Utilizes cc-compliant NaturalEarth data as a template (housed in the maps subdirectory).
* Custom markers can be input using lat/lon coords under self.content['irregular_markers'].
* Labels for countries, cities, and irregular markers can be adjusted for size and position via the _label_adjuster() function. 
* Script is able to output chloropleth maps; however, (csv) input data must be formatted correctly (the current mapper.py has Ontario renewables data input and adjusted as an example)

## Examples

### Ukraine War Map
![Ukraine-War_ex1](https://github.com/zbonalldaylong/Mapper/assets/77871506/07c867f8-fb80-40f8-a541-dab9b6947361)

### DRC Food Scarcity
![DRC-Food_Insecurity](https://github.com/zbonalldaylong/Mapper/assets/77871506/af9145a2-4b6f-4929-bdfc-d4230b38f528)

### Ontario Renewable Projects Pipeline
![OntarioRenewables_ex2](https://github.com/zbonalldaylong/Mapper/assets/77871506/dd39b1d8-2ffc-4555-aa3f-7eb8fc6b9297)


## Running from Command Line 

Command line syntax: 

###Flags
-h : display help
-mtoken : provide your own mapbox token to generate base map (see: https://docs.mapbox.com/help/getting-started/access-tokens/)

###Display Toggles
-snats : display subnational borders for states/provinces (default off) 
-natlabels : display state labels (default off)
-snatlabels : display subnational labels (default off)

###Features
-nat_list country1+country2+country3, etc. : specify which countries to include on map; use _ for spaces ('United_States_of_America')
-snat_list snat1+snat2+snat3, etc. : specify which provinces to include on map; use _ for spaces ('British_Columbia')
-city_list city1+city2+city3, etc. : specify cities to include on map; use _ for spaces ('Addis_Ababa')

###Custom Features / Markers

Custom features will be loaded and mapped automatically if the features subdirectory contains a file named feature_1.geojson; other features will be loaded as well (feature_2.geojson, etc.)
Refer to custom feature styling options below to customize their appearance. 

-cmarker name>lon>lat>label_position :  Place a custom point on the map by longitude and latitude (example: Taj_Mahal>78.04206>27.17389>middle_right)

###Formatting Toggles
-background_color : Override the background color of the map (formatted as color code; default #ede7f1)
-nat_border_opacity : Override opacity of national borders (default 1)
-nat_border_width : Override width of national borders (default 1) 
-nat_border_color :Override color of national borders (default #282828)
-subnat_border_opacity : Override opacity of subnational borders (default 0.5)
-subnat_border_width : Override width of subnational borders (default 0.5)
-subnat_border_color : Override color of subnational borders (default #282828)

Markers/Cities
-city_text_size : Override text size of city labels (default 12)
-city_text_color : Override text color for city labels (default #241f20)
-marker_size : Override size of marker for cities (default 8)
-marker_color : Override color of marker for cities (default #241f20)

Labels
-nat_label_opacity : Override opacity of national labels (default 0.7)
-nat_label_size : Override text size for national labels (default 30)
-nat_label_color : Overide color for national labels (default #282828)
-subnat_label_opacity : Override opacity for subnational labels (default 0.5)
-subnat_label_size : Override text size for subnational labels (default 15)
-subnat_label_color : Override color for subnational labels (default #282828)

Custom Feature Styling (geojsons)
-feature_color : note format this as a rgba color code to adjust opacity (default rgba(202, 52, 51, 0.5))
-feature_fill_opacity : (default 0.25)
-feature_border_opacity : (default 0.75)
-feature_border_width : (default 1)
-feature_border_color : (default #282828)

###Label Adjustments

Labels occasionally require manual adjustment depending on map context. This can be achieved using the following commands:

-labelpos : Changes label position of a city or feature; format as city+label_position 
Note: Label position options include 'top right' 'bottom right' 'top left' 'middle left' 'top center', etc. 
Examples: -labelpos Vancouver>middle_right+Kamloops>bottom_left

-labeladjust : Changes the size and position of subnat and nat labels ; format as label_name>label_position>shift_extent+size 
Note: Label shifting extent is approximately 4 per inch ; label size is a multiplier of current value (for example, 2 is 2x) ; countries can be repeated for finishing touches 
Examples: -labeladjust United_States_of_America>top_left>10>2+Canada>bottom_left>4>1


###Examples

python mapper.py -nat_list Ukraine -city_list Odesa+Donetsk+Kharkiv -snats -cfeature Zaporizhzhia_Nuclear_Plant>34.584>47.50>bottom_right

python mapper.py -nat_list Canada+United_States_of_America -city_list Vancouver+Kamloops -labelpos Vancouver>middle_right+Kamloops>top_center -labeladjust United_States_of_America>top_left>1.8>0.8+Canada>bottom_left>20>1.3+Canada>left>4>1 -snats -cfeature HMS_Invincible_Site>6.123>57.044444>middle_right+Pole_of_Inacces
sibility>-96.45>62.4>middle_left



