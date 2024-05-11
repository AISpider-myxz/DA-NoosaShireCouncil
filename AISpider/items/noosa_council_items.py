from scrapy import Field
from . import BaseItem


# class AispiderItem(scrapy.Item):
#     # define the fields for your item here like:
#     # name = scrapy.Field()
#     pass

class NoosaCouncilItem(BaseItem):
    application_id = Field()
    application_type = Field()
    category = Field()
    lodgement_date = Field()
    description = Field()
    details = Field()
    decision = Field()
    officer = Field()
    property_id = Field()
    address = Field()
    land_description = Field()
    names = Field()
    documents = Field()

    class Meta:
        table = 'noosa_council'
        unique_fields = ['application_id']