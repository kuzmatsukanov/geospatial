import ee
import pandas as pd


class EEOperator:
    def __init__(self, project_name):
        """Initialize the EE library"""
        ee.Initialize(project=project_name)
        pass

    def get_median(self, image, aoi, scale, band_name):
        """
        Calculate median satellite data value of image
        :param image: ee.image.Image
        :param aoi: ee.geometry.Geometry, area of interest (Polygon)
        :param scale: float, spatial resolution in meters
        :param band_name: str, e.g. 'NDVI'
        :return: median value over the image
        """
        median = image.reduceRegion(ee.Reducer.median(), aoi, scale).get(band_name)
        return image.set('date', image.date().format()).set('median_val', median)

    def get_ee_median_ts(self, dataset_name, start_date, end_date, aoi, scale, band_name):
        """
        Get timeseries of median values of Earth Engine satellite data (e.g. NDVI).
        :param dataset_name: str, e.g. 'COPERNICUS/S2_SR'
        :param start_date:
        :param end_date:
        :param aoi: ee.geometry.Geometry, area of interest (Polygon)
        :param scale: float, spatial resolution in meters
        :param band_name: str, e.g. 'NDVI'
        :return: DataFrame, |date| median value over polygon|
        """
        # Create an image collection containing satellite data
        coll = ee.ImageCollection(dataset_name).select(band_name).filterDate(start_date, end_date).filterBounds(aoi)

        # Get median values over the area of interest for each image
        median_coll = coll.map(lambda image: self.get_median(image, aoi, scale, band_name))

        # Convert the image collection to a time series
        median_ts = median_coll.reduceColumns(ee.Reducer.toList(2), ['date', 'median_val']).get('list')

        # Convert to DataFrame
        df = pd.DataFrame(median_ts.getInfo(), columns=['date', 'median_' + band_name])
        df['date'] = pd.to_datetime(df['date'])
        return df
