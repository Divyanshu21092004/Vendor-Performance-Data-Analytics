import sqlite3
import pandas as pd
import logging
from ingestion_db import ingest_db

logging.basicConfig(
    filename="log/get_vendor_summary.log",
    level= logging.DEBUG,
    format= "%(asctime)s - %(levelname)s - %(message)s",
    filemode= "a"
)

def create_vendor_summary(conn):
    '''this function will merge the different tables to get the overall vendor summary and adding new columns in the resultant data'''

    vendor_sales_summary = pd.read_sql_query("""
    WITH freight_summary AS (
        SELECT
            VendorNumber,
            SUM(Freight) AS FreightCost
        FROM vendor_invoice
        GROUP BY VendorNumber
    ),
    purchase_summary AS (
    SELECT
        p.VendorName,
        p.VendorNumber,
        p.Brand,
        pp.Description,
        p.PurchasePrice,
        pp.Volume,
        pp.Price AS ActualPrice,
        SUM(p.Quantity) AS TotalPurchaseQuantity,
        SUM(p.Dollars) AS TotalPurchaseDollars
    FROM purchases p
    JOIN purchase_prices pp
        ON p.Brand = pp.Brand
    WHERE p.PurchasePrice > 0
    GROUP BY
        p.VendorName,
        p.VendorNumber,
        p.Brand,
        pp.Description,
        p.PurchasePrice,
        pp.Volume,
        pp.Price
    ),
    
    sales_summary AS (
        SELECT
            VendorNo,
            Brand,
            SUM(SalesDollars) AS TotalSalesDollars,
            SUM(SalesPrice) AS TotalSalesPrice,
            SUM(SalesQuantity) AS TotalSalesQuantity,
            SUM(ExciseTax) AS TotalExciseTax
        FROM sales
        GROUP BY VendorNo, Brand
    )
    
    SELECT
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.ActualPrice,
        ps.Volume,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        ss.TotalSalesQuantity,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalExciseTax,
        fs.FreightCost
    FROM purchase_summary ps
    LEFT JOIN sales_summary ss
        ON ps.VendorNumber = ss.VendorNo
        AND ps.Brand = ss.Brand
    LEFT JOIN freight_summary fs
        ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchaseDollars DESC
    """, conn)
    return vendor_sales_summary



def clean_data(df):
    '''this function will clean the data'''

    # changing datatype to float
    df['Volume'] = df['Volume'].astype('float')

    # filling missing value with 0
    df.fillna(0, inplace=True)

    # removing spaces from categorical columns
    df['VendorName'] = df['VendorName'].str.strip()
    df['Description'] = df['Description'].str.strip()

    # creating new columns for better analysis
    vendor_sales_summary['GrossProfit'] = (
        vendor_sales_summary['TotalSalesDollars']
        - vendor_sales_summary['TotalPurchaseDollars']
    )

    vendor_sales_summary['ProfitMargin'] = (
        vendor_sales_summary['GrossProfit']
        / vendor_sales_summary['TotalSalesDollars']
    ) * 100

    vendor_sales_summary['StockTurnover'] = (
        vendor_sales_summary['TotalSalesQuantity']
        / vendor_sales_summary['TotalPurchaseQuantity']
    )

    vendor_sales_summary['SalesToPurchaseRatio'] = (
        vendor_sales_summary['TotalSalesDollars']
        / vendor_sales_summary['TotalPurchaseDollars']
    )

    return df

if __name__ == '__main__':

    conn=sqlite3.connect('inventory.db')

    logging.info( ' creating_vendor_summary_table....')
    summary_df = create_vendor_summary(conn)
    logging.info(summary_df.head())

    logging.info('Cleaning Data.....')
    clean_df = clean_data(summary_df)
    logging.info(clean_df.head())

    logging.info('Ingesting data.....')
    ingest_db(clean_df, 'vendor_sales_summary', conn)
    logging.info('Completed')
    



    
