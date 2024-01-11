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

