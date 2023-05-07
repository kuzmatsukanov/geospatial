import zipfile
from qgis.core import QgsApplication, QgsVectorLayer, QgsCoordinateReferenceSystem, QgsRasterLayer, \
    QgsAggregateCalculator
import utm
import pyproj
import numpy as np
from osgeo import gdal


class QgisOperator:
    def __init__(self, qgis_install_dir="/Applications/QGIS.app"):
        """
        Initializes QGIS in non-GUI mode
        :param qgis_install_dir: str, the QGIS installation directory
        """
        # Initialize a new instance of the QgsApplication in non-GUI mode
        self._qgs = QgsApplication([], False)

        # Set the path to the QGIS installation directory. With adding the QGIS plugins.
        self._qgs.setPrefixPath(qgis_install_dir, True)

        # Initialize QGIS
        self._qgs.initQgis()

        # Initialize the QGIS processing framework
        import processing
        from processing.core.Processing import Processing
        Processing.initialize()
        pass

    def quit(self):
        """Quit QGIS"""
        self._qgs.quit()

    @staticmethod
    def get_shp_file_path_from_zip(zip_path):
        """
        Return the first SHP file path in the ZIP archive.
        :param zip_path: str, ZIP file path
        :return: str, SHP file path
        """
        # Open the ZIP archive in read-only mode
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            # Get a list of all file names in the archive
            file_names = zip_file.namelist()

            # Find the first SHP file in the archive
            shp_file_path = next((name for name in file_names if name.endswith('.shp')), None)
        return shp_file_path

    def load_vector_layer_from_zip(self, zip_path, layer_name='data_points'):
        """
        Returns a QGIS vector layer from zip file. It uses the first SHP file in the zip.
        :param zip_path: str, ZIP file path
        :param layer_name: str
        :return: QGIS vector layer
        """
        # Get SHP file path from the zip archive
        shp_path = QgisOperator.get_shp_file_path_from_zip(zip_path)

        # Load a vector layer from a zip file using "/vsizip/"
        layer = QgsVectorLayer('/vsizip/' + zip_path + '/' + shp_path,
                               layer_name,
                               'ogr')
        return layer

    def convert_layer_wgs84_to_utm(self, layer_wgs84):
        """
        Converts projection of QGIS layer from WGS84 to UTM
        :param layer_wgs84: QGIS Vector layer in WGS84 projection
        :return: QGIS Vector layer in UTM projection
        """
        # Get WGS84 coordinates of the layer's center
        lonlat_center = layer_wgs84.extent().center()

        # Get the UTM zone number
        utm_zone_number = utm.latlon_to_zone_number(latitude=lonlat_center.y(),
                                                    longitude=lonlat_center.x())

        # Get EPSG code of the UTM zone
        utm_crs = pyproj.CRS.from_dict({
            'proj': 'utm',
            'zone': utm_zone_number,
            'south': lonlat_center.y() < 0,  # True if in South Hemisphere
            'ellps': 'WGS84',
            'datum': 'WGS84',
            'units': 'm'
        })
        epsg_code = utm_crs.to_epsg()

        # Convert from WGS84 to UTM
        target_crs = QgsCoordinateReferenceSystem('EPSG:{}'.format(epsg_code))
        params = {
            'INPUT': layer_wgs84,
            'TARGET_CRS': target_crs,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        layer_utm = processing.run("native:reprojectlayer", params)['OUTPUT']
        return layer_utm

    def rasterize_layer(self, layer_dp_utm, PIXEL_SIZE):
        """
        Rasterize QGIS Vector layer (in UTM)
        :param layer_dp_utm: QGIS Vector layer (in UTM)
        :param PIXEL_SIZE: int, in meters
        :return: QGIS Raster layer
        """
        params = {
            'INPUT': layer_dp_utm,
            'FIELD': 'Elevation',
            'BURN': 0,
            'USE_Z': False,
            'UNITS': 1,
            'WIDTH': PIXEL_SIZE,
            'HEIGHT': PIXEL_SIZE,
            'EXTENT': None,
            'NODATA': 0,
            'OPTIONS': '',
            'DATA_TYPE': 5,
            'INIT': None,
            'INVERT': False,
            'EXTRA': '',
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        raster_path = processing.run("gdal:rasterize", params)['OUTPUT']
        raster_layer = QgsRasterLayer(raster_path, "Raster_{}".format(PIXEL_SIZE))
        return raster_layer

    def get_slope_layer(self, raster_layer):
        """
        Calculate Slope values of QGIS raster layer
        :param raster_layer: QGIS Raster layer
        :return: QGIS Raster layer with Slope values
        """
        params = {
            'INPUT': raster_layer,
            'BAND': 1,
            'SCALE': 1,
            'AS_PERCENT': True,
            'COMPUTE_EDGES': True,
            'ZEVENBERGEN': False,
            'OPTIONS': '',
            'EXTRA': '',
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        slope_path = processing.run("gdal:slope", params)['OUTPUT']
        slope_layer = QgsRasterLayer(slope_path, "Slope")
        return slope_layer

    def get_aspect_layer(self, raster_layer):
        """
        Calculate Aspect values of QGIS raster layer
        :param raster_layer: QGIS Raster layer
        :return: QGIS Raster layer with Aspect values
        """
        params = {
            'INPUT': raster_layer,
            'BAND': 1,
            'TRIG_ANGLE': False,
            'ZERO_FLAT': False,
            'COMPUTE_EDGES': True,
            'ZEVENBERGEN': False,
            'OPTIONS': '',
            'EXTRA': '',
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        aspect_path = processing.run("gdal:aspect", params)['OUTPUT']
        aspect_layer = QgsRasterLayer(aspect_path, "Aspect")
        return aspect_layer

    def get_mean_value_of_field_layer(self, layer, field_name):
        """
        Calculate mean value of the field in the QGIS Vector layer.
        :param layer: QGIS Vector layer
        :param field_name: str
        :return: mean value of the field over the layer
        """
        mean_value = layer.aggregate(QgsAggregateCalculator.Mean, field_name)[0]
        return mean_value

    def get_mode_continuus(self, layer, field_name, NUM_OF_BINS, range_tuple):
        """
        Calculate mode value of the continuus field in the QGIS Vector layer.
        :param layer: QGIS Vector layer
        :param field_name: str
        :param NUM_OF_BINS: int
        :param range_tuple: tuple, range of values
        :return: mean value of the continuus field over the layer
        """
        field_val_lst = np.array([f[field_name] for f in layer.getFeatures() if f[field_name] is not None],
                                 dtype=np.float16)
        hist = np.histogram(field_val_lst, bins=NUM_OF_BINS, range=range_tuple)

        max_bin_index = np.argmax(hist[0])
        mode_val = hist[1][max_bin_index] + (360/NUM_OF_BINS)/2
        return mode_val

    def sample_raster_values(self, raster_layer, vector_layer, COLUMN_PREFIX):
        """
        Sample raster values at data points of the given QGIS Vector layer.
        :param raster_layer: QGIS Raster layer where sample from
        :param vector_layer: QGIS Vector layer with the points
        :param COLUMN_PREFIX: str
        :return: QGIS Vector layer with sampled data
        """
        params = {
            'INPUT': vector_layer,
            'RASTERCOPY': raster_layer,
            'COLUMN_PREFIX': COLUMN_PREFIX,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        vector_layer = processing.run("native:rastersampling", params)['OUTPUT']
        return vector_layer

    def get_area_occupied_by_pixels(self, raster_layer, PIXEL_SIZE):
        """
        Calculates area occupied by pixels for QGIS raster layer in meters**2
        :param raster_layer: QGIS Raster layer
        :param PIXEL_SIZE: in meters
        :return: area in m^2
        """
        res = \
        processing.run("native:rasterlayerzonalstats", {
            'INPUT': raster_layer,
            'BAND': 1,
            'ZONES': raster_layer,
            'ZONES_BAND': 1,
            'REF_LAYER': 1,
            'OUTPUT_TABLE': 'TEMPORARY_OUTPUT'})
        area = round((res['TOTAL_PIXEL_COUNT'] - res['NODATA_PIXEL_COUNT']) * PIXEL_SIZE**2)
        return area

    @staticmethod
    def get_interquantile(a, q1=5, q2=95):
        """
        Filter out values fallen out the interpercentile range.
        a: (np.array)
        """
        quantiles = np.percentile(a, q=[q1, q2])
        index_to_have = np.where((a > quantiles[0]) & (a < quantiles[1]))[0]
        return a[index_to_have]

    @staticmethod
    def get_stat_values(a):
        """
        Get statistics values of np.array. Returns dictionary.
        """
        a_dict = {'mean': np.mean(a),
                  'std': np.std(a),
                  'median': np.median(a)}
        return a_dict

    def get_stat_from_shp_file(self, zip_path, field_name_dict):
        """
        Get statistics values of the given fields in the Vector layer
        :param zip_path:  str, ZIP file path
        :param field_name_dict:  dictionary of fields with dtype,
            e.g. {'Elevation': np.float32, 'IsoTime': 'datetime64[s]'}
        :return: field_name_dict
        """

        # Open the shapefile
        shp_path = self.get_shp_file_path_from_zip(zip_path)
        dataset = gdal.OpenEx('/vsizip/' + zip_path + '/' + shp_path, gdal.OF_VECTOR)

        # Get the first layer
        layer = dataset.GetLayer()

        # Get number of data points (rows) in the layer
        size = layer.GetFeatureCount()

        # Get the field indexes and prepare the dictionary
        layer_schema_info = layer.GetLayerDefn()
        for field_name, field_dtype in zip(field_name_dict.keys(), field_name_dict.values()):
            field_name_dict[field_name] = {'dtype': field_dtype}
            field_name_dict[field_name]['index'] = layer_schema_info.GetFieldIndex(field_name)
            field_name_dict[field_name]['data'] = np.empty(size, dtype=field_name_dict[field_name]['dtype'])

        # Get the correspondent data from the layer as np.array. feature is a row
        for i, feature in enumerate(layer):
            for field_name in field_name_dict.keys():
                field_name_dict[field_name]['data'][i] = feature.GetField(field_name_dict[field_name]['index'])

        # Filter out values fallen out the interpercentile range.
        for field_name in field_name_dict.keys():
            field_name_dict[field_name]['data'] = self.get_interquantile(field_name_dict[field_name]['data'],
                                                                         q1=1, q2=95)

        # Get statistics values
        for field_name in field_name_dict.keys():
            field_name_dict[field_name]['stat_val'] = self.get_stat_values(field_name_dict[field_name]['data'])

        # To have only stat_val in the dictionary
        field_name_stat_val_dict = \
            {field_name: field_name_dict[field_name]['stat_val'] for field_name in field_name_dict}
        return field_name_stat_val_dict
