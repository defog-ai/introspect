import os
import time

from db_models import Metadata
from sqlalchemy import create_engine, insert, delete

SALT = "TOMRIDDLEISVOLDEMORT"


db_creds = {
    "user": os.environ.get("DBUSER", "postgres"),
    "password": os.environ.get("DBPASSWORD", "postgres"),
    "host": os.environ.get("DBHOST", "agents-postgres"),
    "port": os.environ.get("DBPORT", "5432"),
    "database": os.environ.get("DATABASE", "postgres"),
}


# connect to the main database
connection_uri = f"postgresql://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"
engine = create_engine(connection_uri, echo=True)
print("Connected to database")

# insert glossary prunable units
t_start = time.time()

# insert metadata for restaurant
restaurant_metadata = {
    "location": [
        {
            "data_type": "bigint",
            "column_name": "restaurant_id",
            "column_description": "Unique identifier for each restaurant",
        },
        {
            "data_type": "bigint",
            "column_name": "house_number",
            "column_description": "The number assigned to the building where the restaurant is located",
        },
        {
            "data_type": "text",
            "column_name": "street_name",
            "column_description": "The name of the street where the restaurant is located",
        },
        {
            "data_type": "text",
            "column_name": "city_name",
            "column_description": "The name of the city where the restaurant is located",
        },
    ],
    "geographic": [
        {
            "data_type": "text",
            "column_name": "city_name",
            "column_description": "The name of the city",
        },
        {
            "data_type": "text",
            "column_name": "county",
            "column_description": "The name of the county",
        },
        {
            "data_type": "text",
            "column_name": "region",
            "column_description": "The name of the region",
        },
    ],
    "restaurant": [
        {
            "data_type": "bigint",
            "column_name": "id",
            "column_description": "Unique identifier for each restaurant",
        },
        {
            "data_type": "real",
            "column_name": "rating",
            "column_description": "The rating of the restaurant on a scale of 0 to 5",
        },
        {
            "data_type": "text",
            "column_name": "name",
            "column_description": "The name of the restaurant",
        },
        {
            "data_type": "text",
            "column_name": "food_type",
            "column_description": "The type of food served at the restaurant",
        },
        {
            "data_type": "text",
            "column_name": "city_name",
            "column_description": "The city where the restaurant is located",
        },
    ],
}
restaurant_api_key = "Restaurant"

try:
    with engine.begin() as conn:
        # delete all existing metadata for the restaurant api key
        conn.execute(delete(Metadata).where(Metadata.db_name == restaurant_api_key))
        for table in restaurant_metadata:
            for column in restaurant_metadata[table]:
                conn.execute(
                    insert(Metadata).values(
                        db_name=restaurant_api_key,
                        table_name=table,
                        column_name=column["column_name"],
                        data_type=column["data_type"],
                        column_description=column["column_description"],
                    )
                )
except Exception as e:
    print(f"Error inserting metadata for ({restaurant_api_key}) into metadata:\n{e}")


# insert metadata for accounts
accounts_metadata = {
    "accounts": [
        {
            "data_type": "integer",
            "column_name": "account_id",
            "column_description": "Unique identifier for each account",
        },
        {
            "data_type": "integer",
            "column_name": "customer_id",
            "column_description": "Identifier for the customer associated with the account",
        },
        {
            "data_type": "character varying",
            "column_name": "account_alias",
            "column_description": "Alias used by the customer to identify the account",
        },
    ],
    "customers": [
        {
            "data_type": "integer",
            "column_name": "customer_id",
            "column_description": "Unique identifier for each customer",
        },
        {"data_type": "character varying", "column_name": "customer_first_name"},
        {"data_type": "character varying", "column_name": "customer_last_name"},
    ],
    "customers_cards": [
        {
            "data_type": "integer",
            "column_name": "card_id",
            "column_description": "Unique identifier for each card",
        },
        {"data_type": "integer", "column_name": "customer_id"},
        {"data_type": "character varying", "column_name": "card_type_code"},
        {"data_type": "character varying", "column_name": "card_number"},
        {
            "data_type": "date",
            "column_name": "date_valid_from",
            "column_description": "Date from which the card is valid",
        },
        {
            "data_type": "date",
            "column_name": "date_valid_to",
            "column_description": "Date until which the card is valid",
        },
    ],
    "financial_transactions": [
        {
            "data_type": "integer",
            "column_name": "transaction_id",
            "column_description": "Unique identifier for each transaction",
        },
        {
            "data_type": "integer",
            "column_name": "account_id",
            "column_description": "Identifier for the account associated with the transaction",
        },
        {
            "data_type": "integer",
            "column_name": "card_id",
            "column_description": "Identifier for the card used for the transaction",
        },
        {"data_type": "character varying", "column_name": "transaction_type"},
        {"data_type": "date", "column_name": "transaction_date"},
        {
            "data_type": "double precision",
            "column_name": "transaction_amount",
            "column_description": "Amount of the transaction in US$",
        },
    ],
}


accounts_api_key = "Cards"

try:
    with engine.begin() as conn:
        # delete all existing metadata for the accounts api key
        conn.execute(delete(Metadata).where(Metadata.db_name == accounts_api_key))
        for table in accounts_metadata:
            for column in accounts_metadata[table]:
                conn.execute(
                    insert(Metadata).values(
                        db_name=accounts_api_key,
                        table_name=table,
                        column_name=column["column_name"],
                        data_type=column["data_type"],
                        column_description=column["column_description"],
                    )
                )
except Exception as e:
    print(f"Error inserting metadata for ({accounts_api_key}) into metadata:\n{e}")


accounts_metadata_imported = {
    "web_analytics": [
        {
            "data_type": "character varying",
            "column_name": "card_number",
            "column_description": "Card number associated with purchase",
        },
        {"data_type": "character varying", "column_name": "product_purchased_name"},
        {
            "data_type": "double precision",
            "column_name": "product_price",
            "column_description": "Price of product in US$",
        },
        {
            "data_type": "timestamp without time zone",
            "column_name": "purchase_datetime",
        },
    ]
}

# insert metadata for housing
housing_metadata = {
    "postal_districts": [
        {
            "data_type": "INTEGER",
            "column_name": "postal_district",
            "column_description": "",
        },
        {
            "data_type": "TEXT",
            "column_name": "postal_sector",
            "column_description": "comma separated list of first 2 digits of postal codes",
        },
        {
            "data_type": "TEXT",
            "column_name": "general_location",
            "column_description": "comma separated list of district names",
        },
    ],
    "pri_schools": [
        {"data_type": "TEXT", "column_name": "school_name", "column_description": ""},
        {"data_type": "TEXT", "column_name": "url_address", "column_description": ""},
        {"data_type": "TEXT", "column_name": "address", "column_description": ""},
        {
            "data_type": "INTEGER",
            "column_name": "postal_code",
            "column_description": "",
        },
        {
            "data_type": "INTEGER",
            "column_name": "telephone_no",
            "column_description": "",
        },
        {
            "data_type": "TEXT",
            "column_name": "telephone_no_2",
            "column_description": "",
        },
        {"data_type": "INTEGER", "column_name": "fax_no", "column_description": ""},
        {"data_type": "TEXT", "column_name": "fax_no_2", "column_description": ""},
        {"data_type": "TEXT", "column_name": "email_address", "column_description": ""},
        {
            "data_type": "TEXT",
            "column_name": "mrt_desc",
            "column_description": "comma separated list of nearest MRT stations",
        },
        {
            "data_type": "TEXT",
            "column_name": "bus_desc",
            "column_description": "comma separated list of bus services",
        },
        {
            "data_type": "TEXT",
            "column_name": "principal_name",
            "column_description": "",
        },
        {"data_type": "TEXT", "column_name": "first_vp_name", "column_description": ""},
        {
            "data_type": "TEXT",
            "column_name": "second_vp_name",
            "column_description": "",
        },
        {"data_type": "TEXT", "column_name": "third_vp_name", "column_description": ""},
        {
            "data_type": "TEXT",
            "column_name": "fourth_vp_name",
            "column_description": "",
        },
        {"data_type": "TEXT", "column_name": "fifth_vp_name", "column_description": ""},
        {"data_type": "TEXT", "column_name": "sixth_vp_name", "column_description": ""},
        {
            "data_type": "TEXT",
            "column_name": "dgp_code",
            "column_description": "name of district, development guide plan",
        },
        {
            "data_type": "TEXT",
            "column_name": "zone_code",
            "column_description": "name of zone, can only be 'NORTH', 'SOUTH', 'EAST', 'WEST'",
        },
        {
            "data_type": "TEXT",
            "column_name": "type_code",
            "column_description": "type of school, can only be 'GOVERNMENT SCHOOL', 'GOVERNMENT-AIDED SCH', 'INDEPENDENT SCHOOL', 'SPECIALISED SCHOOL'",
        },
        {
            "data_type": "TEXT",
            "column_name": "nature_code",
            "column_description": "gender mix of school, can only be 'CO-ED SCHOOL', 'BOYS'' SCHOOL', 'GIRLS'' SCHOOL'",
        },
        {
            "data_type": "TEXT",
            "column_name": "session_code",
            "column_description": "type of session, can only be 'FULL DAY', 'SINGLE SESSION', 'DOUBLE SESSION'",
        },
        {
            "data_type": "TEXT",
            "column_name": "mainlevel_code",
            "column_description": "level of school, can only be 'PRIMARY', 'SECONDARY', 'JUNIOR COLLEGE', 'MIXED LEVELS', 'CENTRALISED INSTITUTE'",
        },
        {
            "data_type": "TEXT",
            "column_name": "sap_ind",
            "column_description": "whether school is a Special Assistance Plan school, can only be 'Yes', 'No'",
        },
        {
            "data_type": "TEXT",
            "column_name": "autonomous_ind",
            "column_description": "whether school is an Autonomous school, can only be 'Yes', 'No'",
        },
        {
            "data_type": "TEXT",
            "column_name": "gifted_ind",
            "column_description": "whether school is a Gifted Education Programme school, can only be 'Yes', 'No'",
        },
        {
            "data_type": "TEXT",
            "column_name": "ip_ind",
            "column_description": "whether school offers Integrated Programme, can only be 'Yes', 'No'",
        },
        {
            "data_type": "TEXT",
            "column_name": "mothertongue1_code",
            "column_description": "first language taught in school, can only be 'Chinese', 'Malay', 'Tamil'",
        },
        {
            "data_type": "TEXT",
            "column_name": "mothertongue2_code",
            "column_description": "second language taught in school, can only be 'Chinese', 'Malay', 'Tamil'",
        },
        {
            "data_type": "TEXT",
            "column_name": "mothertongue3_code",
            "column_description": "third language taught in school, can only be 'Chinese', 'Malay', 'Tamil'",
        },
    ],
    "condos": [
        {
            "data_type": "TEXT",
            "column_name": "project_name",
            "column_description": "name of condo",
        },
        {
            "data_type": "INTEGER",
            "column_name": "transacted_price_dollar",
            "column_description": "transacted sale price in dollars",
        },
        {
            "data_type": "REAL",
            "column_name": "area_sqft",
            "column_description": "area in square feet",
        },
        {
            "data_type": "INTEGER",
            "column_name": "unit_price_dollar_psf",
            "column_description": "unit sale price in dollars per square foot",
        },
        {"data_type": "DATE", "column_name": "sale_date", "column_description": ""},
        {"data_type": "TEXT", "column_name": "street_name", "column_description": ""},
        {
            "data_type": "TEXT",
            "column_name": "type_of_sale",
            "column_description": "type of sale, can only be 'New Sale', 'Sub Sale', 'Resale'",
        },
        {
            "data_type": "TEXT",
            "column_name": "type_of_area",
            "column_description": "type of area, can only be 'Strata', 'Land'",
        },
        {
            "data_type": "INTEGER",
            "column_name": "area_sqm",
            "column_description": "area in square meters",
        },
        {
            "data_type": "INTEGER",
            "column_name": "unit_price_dollar_psm",
            "column_description": "unit sale price in dollars per square meter",
        },
        {
            "data_type": "TEXT",
            "column_name": "nett_pricedollar",
            "column_description": "ignore this column",
        },
        {
            "data_type": "TEXT",
            "column_name": "property_type",
            "column_description": "type of property, can only be 'Condominium', 'Apartment'",
        },
        {
            "data_type": "INTEGER",
            "column_name": "number_of_units",
            "column_description": "",
        },
        {
            "data_type": "TEXT",
            "column_name": "tenure",
            "column_description": "tenure of property, can only be 'Freehold', '99 yrs lease commencing from XXXX', 'XXX yrs lease commencing from XXXX'",
        },
        {
            "data_type": "INTEGER",
            "column_name": "postal_district",
            "column_description": "postal district number",
        },
        {
            "data_type": "TEXT",
            "column_name": "market_segment",
            "column_description": "market segment, can only be 'Outside Central Region', 'Core Central Region', 'Rest of Central Region'",
        },
        {
            "data_type": "TEXT",
            "column_name": "floor_level",
            "column_description": "floor level of unit, in the format 'XX to XX' e.g. '01 to 05'",
        },
    ],
    "exec_condos": [
        {
            "data_type": "TEXT",
            "column_name": "project_name",
            "column_description": "name of executive condo",
        },
        {
            "data_type": "INTEGER",
            "column_name": "transacted_price_dollar",
            "column_description": "transacted sale price in dollars",
        },
        {
            "data_type": "REAL",
            "column_name": "area_sqft",
            "column_description": "area in square feet",
        },
        {
            "data_type": "INTEGER",
            "column_name": "unit_price_dollar_psf",
            "column_description": "unit sale price in dollars per square foot",
        },
        {"data_type": "DATE", "column_name": "sale_date", "column_description": ""},
        {"data_type": "TEXT", "column_name": "street_name", "column_description": ""},
        {
            "data_type": "TEXT",
            "column_name": "type_of_sale",
            "column_description": "type of sale, can only be 'New Sale', 'Sub Sale', 'Resale'",
        },
        {
            "data_type": "TEXT",
            "column_name": "type_of_area",
            "column_description": "type of area, can only be 'Strata', 'Land'",
        },
        {
            "data_type": "INTEGER",
            "column_name": "area_sqm",
            "column_description": "area in square meters",
        },
        {
            "data_type": "INTEGER",
            "column_name": "unit_price_dollar_psm",
            "column_description": "unit sale price in dollars per square",
        },
        {
            "data_type": "TEXT",
            "column_name": "nett_pricedollar",
            "column_description": "ignore this column",
        },
        {
            "data_type": "TEXT",
            "column_name": "property_type",
            "column_description": "type of property, can only be 'Executive Condominium'",
        },
        {
            "data_type": "INTEGER",
            "column_name": "number_of_units",
            "column_description": "",
        },
        {
            "data_type": "TEXT",
            "column_name": "tenure",
            "column_description": "tenure of property, can only be '99 yrs lease commencing from XXXX'",
        },
        {
            "data_type": "INTEGER",
            "column_name": "postal_district",
            "column_description": "postal district number",
        },
        {
            "data_type": "TEXT",
            "column_name": "market_segment",
            "column_description": "market segment, can only be 'Outside Central Region', 'Core Central Region', 'Rest of Central Region'",
        },
        {
            "data_type": "TEXT",
            "column_name": "floor_level",
            "column_description": "floor level of unit, in the format 'XX to XX' e.g. '01 to 05'",
        },
    ],
    "rental": [
        {
            "data_type": "TEXT",
            "column_name": "project_name",
            "column_description": "name of property",
        },
        {"data_type": "TEXT", "column_name": "street_name", "column_description": ""},
        {
            "data_type": "INTEGER",
            "column_name": "postal_district",
            "column_description": "postal district number",
        },
        {
            "data_type": "TEXT",
            "column_name": "property_type",
            "column_description": "type of property, can only be 'Non-Landed Properties'",
        },
        {
            "data_type": "INTEGER",
            "column_name": "no_of_bedroom",
            "column_description": "",
        },
        {
            "data_type": "TEXT",
            "column_name": "monthly_rent_dollar",
            "column_description": "monthly rent in dollars",
        },
        {
            "data_type": "TEXT",
            "column_name": "floor_area_sqm",
            "column_description": "floor area in square meters",
        },
        {
            "data_type": "TEXT",
            "column_name": "floor_area_sqft",
            "column_description": "floor area in square feet",
        },
        {
            "data_type": "DATE",
            "column_name": "lease_commencement_date",
            "column_description": "",
        },
    ],
}

housing_api_key = "Housing"
try:
    with engine.begin() as conn:
        # delete all existing metadata for the housing api key
        conn.execute(delete(Metadata).where(Metadata.db_name == housing_api_key))
        for table in housing_metadata:
            for column in housing_metadata[table]:
                conn.execute(
                    insert(Metadata).values(
                        db_name=housing_api_key,
                        table_name=table,
                        column_name=column["column_name"],
                        data_type=column["data_type"],
                        column_description=column["column_description"],
                    )
                )
except Exception as e:
    print(f"Error inserting metadata for ({housing_api_key}) into metadata:\n{e}")


# insert metadata for webshop
webshop_api_key = "Webshop"

webshop_metadata = {
    "colors": [
        {
            "data_type": "integer",
            "column_name": "id",
            "column_description": "Primary key, unique identifier for a color",
        },
        {
            "data_type": "text",
            "column_name": "name",
            "column_description": "Name of the color",
        },
        {
            "data_type": "text",
            "column_name": "rgb",
            "column_description": "RGB value of the color",
        },
    ],
    "sizes": [
        {
            "data_type": "integer",
            "column_name": "id",
            "column_description": "Primary key, unique identifier for a size",
        },
        {
            "data_type": "gender",
            "column_name": "gender",
            "column_description": "Gender associated with the size",
        },
        {
            "data_type": "category",
            "column_name": "category",
            "column_description": "Category of the product",
        },
        {
            "data_type": "text",
            "column_name": "size",
            "column_description": "Size label",
        },
        {
            "data_type": "int4range",
            "column_name": "size_us",
            "column_description": "Size range for US sizing",
        },
        {
            "data_type": "int4range",
            "column_name": "size_uk",
            "column_description": "Size range for UK sizing",
        },
        {
            "data_type": "int4range",
            "column_name": "size_eu",
            "column_description": "Size range for EU sizing",
        },
    ],
    "labels": [
        {
            "data_type": "integer",
            "column_name": "id",
            "column_description": "Primary key, unique identifier for a label",
        },
        {
            "data_type": "text",
            "column_name": "name",
            "column_description": "Name of the brand or label",
        },
        {
            "data_type": "text",
            "column_name": "slugname",
            "column_description": "URL-friendly version of the label name",
        },
        {
            "data_type": "bytea",
            "column_name": "icon",
            "column_description": "Binary data for the label's icon",
        },
    ],
    "products": [
        {
            "data_type": "integer",
            "column_name": "id",
            "column_description": "Primary key, unique identifier for a product",
        },
        {
            "data_type": "text",
            "column_name": "name",
            "column_description": "Name of the product",
        },
        {
            "data_type": "integer",
            "column_name": "labelid",
            "column_description": "Foreign key reference to labels table",
        },
        {
            "data_type": "category",
            "column_name": "category",
            "column_description": "Product category",
        },
        {
            "data_type": "gender",
            "column_name": "gender",
            "column_description": "Gender associated with the product",
        },
        {
            "data_type": "boolean",
            "column_name": "currentlyactive",
            "column_description": "Indicates if the product is currently active",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "created",
            "column_description": "Timestamp when the product was created",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "updated",
            "column_description": "Timestamp when the product was last updated",
        },
    ],
    "articles": [
        {
            "data_type": "integer",
            "column_name": "id",
            "column_description": "Primary key, unique identifier for an article",
        },
        {
            "data_type": "integer",
            "column_name": "productid",
            "column_description": "Foreign key reference to products table",
        },
        {
            "data_type": "text",
            "column_name": "ean",
            "column_description": "European Article Number (EAN)",
        },
        {
            "data_type": "integer",
            "column_name": "colorid",
            "column_description": "Foreign key reference to colors table",
        },
        {
            "data_type": "text",
            "column_name": "description",
            "column_description": "Description of the article",
        },
        {
            "data_type": "money",
            "column_name": "originalprice",
            "column_description": "Original price of the article",
        },
        {
            "data_type": "money",
            "column_name": "reducedprice",
            "column_description": "Discounted price of the article",
        },
        {
            "data_type": "numeric",
            "column_name": "taxrate",
            "column_description": "Tax rate applied to the article",
        },
        {
            "data_type": "integer",
            "column_name": "discountinpercent",
            "column_description": "Discount percentage applied",
        },
        {
            "data_type": "boolean",
            "column_name": "currentlyactive",
            "column_description": "Indicates if the article is currently active",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "created",
            "column_description": "Timestamp when the article was created",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "updated",
            "column_description": "Timestamp when the article was last updated",
        },
    ],
    "stock": [
        {
            "data_type": "integer",
            "column_name": "id",
            "column_description": "Primary key, unique identifier for stock entry",
        },
        {
            "data_type": "integer",
            "column_name": "articleid",
            "column_description": "Foreign key reference to articles table",
        },
        {
            "data_type": "integer",
            "column_name": "count",
            "column_description": "Number of articles in stock",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "created",
            "column_description": "Timestamp when the stock record was created",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "updated",
            "column_description": "Timestamp when the stock record was last updated",
        },
    ],
    "order_positions": [
        {
            "data_type": "integer",
            "column_name": "id",
            "column_description": "Primary key, unique identifier for an order position",
        },
        {
            "data_type": "integer",
            "column_name": "orderid",
            "column_description": "Foreign key reference to order table",
        },
        {
            "data_type": "integer",
            "column_name": "articleid",
            "column_description": "Foreign key reference to articles table",
        },
        {
            "data_type": "smallint",
            "column_name": "amount",
            "column_description": "Quantity of the article in the order",
        },
        {
            "data_type": "money",
            "column_name": "price",
            "column_description": "Price of the article",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "created",
            "column_description": "Timestamp when the order position was created",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "updated",
            "column_description": "Timestamp when the order position was last updated",
        },
    ],
    "customer": [
        {
            "data_type": "integer",
            "column_name": "id",
            "column_description": "Primary key, unique identifier for a customer",
        },
        {
            "data_type": "text",
            "column_name": "firstname",
            "column_description": "First name of the customer",
        },
        {
            "data_type": "text",
            "column_name": "lastname",
            "column_description": "Last name of the customer",
        },
        {
            "data_type": "gender",
            "column_name": "gender",
            "column_description": "Gender of the customer",
        },
        {
            "data_type": "text",
            "column_name": "email",
            "column_description": "Email address of the customer",
        },
        {
            "data_type": "date",
            "column_name": "dateofbirth",
            "column_description": "Date of birth of the customer",
        },
        {
            "data_type": "integer",
            "column_name": "currentaddressid",
            "column_description": "Foreign key reference to address table",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "created",
            "column_description": "Timestamp when the customer record was created",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "updated",
            "column_description": "Timestamp when the customer record was last updated",
        },
    ],
    "address": [
        {
            "data_type": "integer",
            "column_name": "id",
            "column_description": "Primary key, unique identifier for an address",
        },
        {
            "data_type": "integer",
            "column_name": "customerid",
            "column_description": "Foreign key reference to customer table",
        },
        {
            "data_type": "text",
            "column_name": "firstname",
            "column_description": "First name of the address holder",
        },
        {
            "data_type": "text",
            "column_name": "lastname",
            "column_description": "Last name of the address holder",
        },
        {
            "data_type": "text",
            "column_name": "address1",
            "column_description": "Primary address line",
        },
        {
            "data_type": "text",
            "column_name": "address2",
            "column_description": "Secondary address line",
        },
        {
            "data_type": "text",
            "column_name": "city",
            "column_description": "City of the address",
        },
        {
            "data_type": "text",
            "column_name": "zip",
            "column_description": "ZIP code of the address",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "created",
            "column_description": "Timestamp when the address record was created",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "updated",
            "column_description": "Timestamp when the address record was last updated",
        },
    ],
    "order": [
        {
            "data_type": "integer",
            "column_name": "id",
            "column_description": "Primary key, unique identifier for an order",
        },
        {
            "data_type": "integer",
            "column_name": "customer",
            "column_description": "Foreign key reference to customer table",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "ordertimestamp",
            "column_description": "Timestamp when the order was placed",
        },
        {
            "data_type": "integer",
            "column_name": "shippingaddressid",
            "column_description": "Foreign key reference to address table",
        },
        {
            "data_type": "money",
            "column_name": "total",
            "column_description": "Total cost of the order",
        },
        {
            "data_type": "money",
            "column_name": "shippingcost",
            "column_description": "Shipping cost for the order",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "created",
            "column_description": "Timestamp when the order was created",
        },
        {
            "data_type": "timestamp with time zone",
            "column_name": "updated",
            "column_description": "Timestamp when the order was last updated",
        },
    ],
}

try:
    with engine.begin() as conn:
        # delete all existing metadata for the webshop api key
        conn.execute(delete(Metadata).where(Metadata.db_name == webshop_api_key))
        for table in webshop_metadata:
            for column in webshop_metadata[table]:
                conn.execute(
                    insert(Metadata).values(
                        db_name=webshop_api_key,
                        table_name=table,
                        column_name=column["column_name"],
                        data_type=column["data_type"],
                        column_description=column["column_description"],
                    )
                )
except Exception as e:
    print(f"Error inserting metadata for ({webshop_api_key}) into metadata:\n{e}")


# Insert metadata for cricket
cricket_api_key = "Cricket"
cricket_metadata = {
    "games": [
        {
            "data_type": "integer",
            "column_name": "match_id",
            "column_description": "Unique identifier for each match",
        },
        {
            "data_type": "varchar(100)",
            "column_name": "team_1_name",
            "column_description": "Name of Team 1",
        },
        {
            "data_type": "varchar(100)",
            "column_name": "team_2_name",
            "column_description": "Name of Team 2",
        },
        {
            "data_type": "integer",
            "column_name": "team_1_id",
            "column_description": "ID of Team 1",
        },
        {
            "data_type": "integer",
            "column_name": "team_2_id",
            "column_description": "ID of Team 2",
        },
        {
            "data_type": "varchar(100)",
            "column_name": "ground_name",
            "column_description": "Name of the ground",
        },
        {
            "data_type": "integer",
            "column_name": "ground_id",
            "column_description": "ID of the ground",
        },
        {
            "data_type": "date",
            "column_name": "match_date",
            "column_description": "Date of the match",
        },
    ],
    "ball_by_ball": [
        {
            "data_type": "serial",
            "column_name": "delivery_id",
            "column_description": "Unique identifier for each delivery",
        },
        {
            "data_type": "integer",
            "column_name": "match_id",
            "column_description": "Foreign key linking to the games table",
        },
        {
            "data_type": "integer",
            "column_name": "inning",
            "column_description": "Inning number (1 or 2)",
        },
        {
            "data_type": "varchar(100)",
            "column_name": "batting_team",
            "column_description": "Name of the batting team",
        },
        {
            "data_type": "varchar(100)",
            "column_name": "bowling_team",
            "column_description": "Name of the bowling team",
        },
        {
            "data_type": "integer",
            "column_name": "batsman",
            "column_description": "Player ID of the batsman",
        },
        {
            "data_type": "integer",
            "column_name": "bowler",
            "column_description": "Player ID of the bowler",
        },
        {
            "data_type": "varchar(100)",
            "column_name": "batsman_name",
            "column_description": "Name of the batsman",
        },
        {
            "data_type": "varchar(100)",
            "column_name": "non_striker",
            "column_description": "Name of the non-striker",
        },
        {
            "data_type": "varchar(100)",
            "column_name": "bowler_name",
            "column_description": "Name of the bowler",
        },
        {
            "data_type": "varchar(1)",
            "column_name": "bat_right_handed",
            "column_description": "Whether batsman is right-handed (y/n)",
        },
        {
            "data_type": "float",
            "column_name": "ovr",
            "column_description": "Over and ball (e.g., 1.2 for second ball of the first over)",
        },
        {
            "data_type": "integer",
            "column_name": "runs_batter",
            "column_description": "Runs scored by the batsman",
        },
        {
            "data_type": "integer",
            "column_name": "runs_w_extras",
            "column_description": "Total runs scored (including extras)",
        },
        {
            "data_type": "integer",
            "column_name": "extras",
            "column_description": "Runs awarded as extras for the ball",
        },
        {
            "data_type": "float",
            "column_name": "x",
            "column_description": "X-coordinate of where the ball traveled",
        },
        {
            "data_type": "float",
            "column_name": "y",
            "column_description": "Y-coordinate of where the ball traveled",
        },
        {
            "data_type": "integer",
            "column_name": "z",
            "column_description": "Zone where the ball traveled",
        },
        {
            "data_type": "float",
            "column_name": "landing_x",
            "column_description": "X-coordinate where the ball landed",
        },
        {
            "data_type": "float",
            "column_name": "landing_y",
            "column_description": "Y-coordinate where the ball landed",
        },
        {
            "data_type": "float",
            "column_name": "ended_x",
            "column_description": "X-coordinate where the ball ended",
        },
        {
            "data_type": "float",
            "column_name": "ended_y",
            "column_description": "Y-coordinate where the ball ended",
        },
        {
            "data_type": "float",
            "column_name": "ball_speed",
            "column_description": "Speed of the delivery in miles per hour",
        },
        {
            "data_type": "integer",
            "column_name": "cumul_runs",
            "column_description": "Cumulative runs at this point in the inning",
        },
        {
            "data_type": "boolean",
            "column_name": "wicket",
            "column_description": "Whether the ball resulted in a wicket (TRUE or FALSE)",
        },
        {
            "data_type": "varchar(100)",
            "column_name": "wicket_method",
            "column_description": "Method of dismissal (e.g., bowled, caught)",
        },
        {
            "data_type": "integer",
            "column_name": "who_out",
            "column_description": "Player ID of the batsman dismissed",
        },
        {
            "data_type": "integer",
            "column_name": "control",
            "column_description": "Whether or not the batsman middled the ball (1=middled, 0=not middled)",
        },
        {
            "data_type": "varchar(50)",
            "column_name": "extras_type",
            "column_description": "Type of extras (e.g., wide, no-ball)",
        },
    ],
}

try:
    with engine.begin() as conn:
        # delete all existing metadata for the cricket api key
        conn.execute(delete(Metadata).where(Metadata.db_name == cricket_api_key))
        for table in cricket_metadata:
            for column in cricket_metadata[table]:
                conn.execute(
                    insert(Metadata).values(
                        db_name=cricket_api_key,
                        table_name=table,
                        column_name=column["column_name"],
                        data_type=column["data_type"],
                        column_description=column["column_description"],
                    )
                )
except Exception as e:
    print(f"Error inserting metadata for ({cricket_api_key}) into metadata:\n{e}")
