# Plotly Mapper

Script to output a customized world map that combines Plotly/Mapbox base map with user-specified data and features (geojson, eg). 

## Notes
* Style, setting, and content attributes input by user before execution.  
* MapBuilder class checks for custom features on inititialization in features sub-directory; named feature_1.geojson, feature_2.geojson, etc. 
* MapBuilder class downloads and unzips geographic data for populated places based on user-specified country (self.content['country_list']) on initialization. 
* Sub-national borders (provinces, states) can be initialized via a settings toggle.
* Custom markers can be input using lat/lon coords under self.content['irregular_markers'].
* Labels for countries, cities, and irregular markers can be adjusted for size and position via the _label_adjuster() function. 
* Script is able to output chloropleth maps; however, (csv) input data must be formatted correctly (the current mapper.py has Ontario renewables data input and adjusted as an example)

## Examples

### Ukraine War Map

### DRC Food Scarcity

### Ontario Renewable Projects Pipeline

