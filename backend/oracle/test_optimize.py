import asyncio
from optimize import optimize

x = {
    "inputs": {
        "user_question": "suggest me restaurants for an outing. I want a variety of cuisines and at least 5 restaurants visited",
        "sources": [],
        "task_type": "optimization",
    },
    "outputs": {
        "gather_context": {
            "problem_statement": "Determine the optimal locations for purchasing condominiums in Singapore based on customer preferences and financial capabilities.",
            "context": "",
            "objective": "Maximize the potential return on investment from property purchases by analyzing financial transactions to assess customer spending patterns and preferences. This will involve aggregating transaction amounts from the financial_transactions table, filtered by transaction types that indicate property-related expenses.",
            "constraints": [],
            "variables": ["property_id", "location", "price", "customer_id"],
            "issues": [
                "The current database schema does not include specific information about properties, such as their locations, prices, or types (e.g., condos). Additional data sources are needed to provide insights into available condominiums in Singapore."
            ],
        },
        "explore": [
            {
                "qn_id": 0,
                "generated_qn": "How do the financial capabilities of customers vary over time based on their transaction amounts?",
                "independent_variable": {
                    "name": "transaction_date",
                    "description": "Date of the financial transaction.",
                    "table.column": ["financial_transactions.transaction_date"],
                },
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "customer_id,customer_first_name,customer_last_name,transaction_date,transaction_amount,cumulative_transaction_amount\n1,John,Doe,2020-01-05,99.990,99.990\n1,John,Doe,2020-02-15,15.000,114.990\n1,John,Doe,2020-03-20,200.000,314.990\n1,John,Doe,2020-04-14,175.000,489.990\n1,John,Doe,2022-01-08,250.000,739.990\n1,John,Doe,2022-02-18,200.000,939.990\n1,John,Doe,2022-03-27,120.000,1059.990\n1,John,Doe,2022-04-15,20.000,1079.990\n1,John,Doe,2023-01-01,49.990,1129.980\n1,John,Doe,2023-02-04,10.000,1139.980\n1,John,Doe,2023-02-14,125.670,1265.650\n1,John,Doe,2023-02-15,20.000,1285.650\n1,John,Doe,2023-03-22,150.000,1435.650\n1,John,Doe,2023-04-09,125.000,1560.650\n1,John,Doe,2024-01-23,74.990,1635.640\n1,John,Doe,2024-02-09,25.000,1660.640\n2,Jane,Doe,2020-05-17,149.990,149.990\n2,Jane,Doe,2020-06-12,20.000,169.990\n2,Jane,Doe,2022-05-24,550.000,719.990\n2,Jane,Doe,2022-06-14,100.000,819.990\n2,Jane,Doe,2023-05-17,59.990,879.980\n2,Jane,Doe,2023-06-03,15.000,894.980\n2,Jane,Doe,2024-03-29,100.000,994.980\n2,Jane,Doe,2024-04-14,75.000,1069.980\n3,Robert,Jones,2020-07-28,100.000,100.000\n3,Robert,Jones,2020-08-05,90.000,190.000\n3,Robert,Jones,2021-01-04,35.200,225.200\n3,Robert,Jones,2021-02-11,50.000,275.200\n3,Robert,Jones,2021-03-19,299.000,574.200\n3,Robert,Jones,2021-04-07,15.000,589.200\n3,Robert,Jones,2023-07-20,99.990,689.190\n3,Robert,Jones,2023-08-12,80.000,769.190\n4,Michael,Lee,2021-05-18,180.000,180.000\n4,Michael,Lee,2021-06-30,200.000,380.000\n4,Michael,Lee,2022-07-16,300.000,680.000\n4,Michael,Lee,2022-08-06,250.000,930.000\n5,William,Chang,2021-07-27,59.990,59.990\n5,William,Chang,2021-08-03,20.000,79.990\n5,William,Chang,2021-09-14,450.000,529.990\n5,William,Chang,2021-10-05,50.000,579.990\n5,William,Chang,2022-09-18,899.990,1479.980\n5,William,Chang,2022-10-12,100.000,1579.980\n5,William,Chang,2023-09-01,199.990,1779.970\n5,William,Chang,2023-10-17,35.000,1814.970\n5,William,Chang,2024-05-05,299.990,2114.960\n5,William,Chang,2024-06-28,50.000,2164.960\n",
                        "artifact_description": "Table showing customer transaction data over time, including transaction amounts and cumulative transaction amounts for each customer.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/123/report_84/q0.png",
                        "artifact_description": "Line chart depicting transaction amounts over time, showing fluctuations in customer spending.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT c.customer_id, c.customer_first_name, c.customer_last_name, ft.transaction_date, ft.transaction_amount, SUM (ft.transaction_amount) OVER (PARTITION BY c.customer_id ORDER BY ft.transaction_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_transaction_amount FROM customers AS c JOIN accounts AS a ON a.customer_id = c.customer_id JOIN financial_transactions AS ft ON ft.account_id = a.account_id;",
                    "chart_fn_params": {
                        "name": "relplot",
                        "parameters": {
                            "kind": "line",
                            "x": "transaction_date",
                            "y": "transaction_amount",
                            "hue": None,
                            "col": None,
                            "row": None,
                        },
                    },
                },
                "title": "Analysis of Customer Financial Transactions Over Time",
                "summary": "The data reveals varying financial capabilities among customers, with some showing consistent spending and others experiencing spikes. This information can help identify potential property buyers in Singapore, particularly for condos, by assessing their financial activity and stability over time.",
            },
            {
                "qn_id": 1,
                "generated_qn": "What are the financial capabilities of customers with different first names based on their transaction amounts?",
                "independent_variable": {
                    "name": "customer_first_name",
                    "description": "First name of the customer.",
                    "table.column": ["customers.customer_first_name"],
                },
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "customer_first_name,total_transaction_amount\nWilliam,2164.960\nJohn,1660.640\nJane,1069.980\nMichael,930.000\nRobert,769.190\n",
                        "artifact_description": "Table showing total transaction amounts by customer first name.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/123/report_84/q1.png",
                        "artifact_description": "Bar chart displaying total transaction amounts for customers with different first names.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT c.customer_first_name, SUM (ft.transaction_amount) AS total_transaction_amount FROM customers AS c JOIN accounts AS a ON c.customer_id = a.customer_id JOIN financial_transactions AS ft ON a.account_id = ft.account_id GROUP BY c.customer_first_name ORDER BY total_transaction_amount DESC NULLS LAST;",
                    "chart_fn_params": {
                        "name": "catplot",
                        "parameters": {
                            "kind": "bar",
                            "x": "customer_first_name",
                            "y": "total_transaction_amount",
                            "hue": None,
                            "col": None,
                            "row": None,
                        },
                    },
                },
                "title": "Analysis of Customer Transaction Amounts by First Name",
                "summary": "The analysis reveals that customers named William have the highest total transaction amount, followed by John and Jane. This suggests that individuals with these names may have higher financial capabilities. This insight could be useful for targeting potential property buyers in Singapore, especially for condos.",
            },
            {
                "qn_id": 2,
                "generated_qn": "How do the financial capabilities of customers vary based on their last names?",
                "independent_variable": {
                    "name": "customer_last_name",
                    "description": "Last name of the customer.",
                    "table.column": ["customers.customer_last_name"],
                },
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "customer_last_name,total_transaction_amount\nDoe,2730.620\nChang,2164.960\nLee,930.000\nJones,769.190\n",
                        "artifact_description": "Table showing total transaction amounts grouped by customer last names.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/123/report_84/q2.png",
                        "artifact_description": "Bar chart displaying total transaction amounts for customers with last names Doe, Chang, Lee, and Jones.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT c.customer_last_name, SUM (ft.transaction_amount) AS total_transaction_amount FROM customers AS c JOIN accounts AS a ON c.customer_id = a.customer_id JOIN financial_transactions AS ft ON a.account_id = ft.account_id GROUP BY c.customer_last_name ORDER BY total_transaction_amount DESC NULLS LAST;",
                    "chart_fn_params": {
                        "name": "catplot",
                        "parameters": {
                            "kind": "bar",
                            "x": "customer_last_name",
                            "y": "total_transaction_amount",
                            "hue": None,
                            "col": None,
                            "row": None,
                        },
                    },
                },
                "title": "Customer Financial Capabilities by Last Name",
                "summary": "The analysis reveals that customers with the last name 'Doe' have the highest total transaction amount, followed by 'Chang', 'Lee', and 'Jones'. This suggests varying financial capabilities among these groups, with 'Doe' being the most financially active.",
            },
            {
                "qn_id": 3,
                "generated_qn": "What is the distribution of transaction amounts based on the type of card used by customers?",
                "independent_variable": {
                    "name": "card_type_code",
                    "description": "Type of card used for the transaction.",
                    "table.column": ["customers_cards.card_type_code"],
                },
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "card_type_code,transaction_amount,distribution\nAMEX,20.000,0.333\nAMEX,20.000,0.333\nAMEX,59.990,0.500\nAMEX,125.000,0.667\nAMEX,149.990,0.833\nAMEX,150.000,1.000\nDISC,50.000,0.500\nDISC,50.000,0.500\nDISC,299.990,0.750\nDISC,450.000,1.000\nMC,15.000,0.050\nMC,20.000,0.100\nMC,35.000,0.150\nMC,35.200,0.200\nMC,50.000,0.250\nMC,59.990,0.300\nMC,75.000,0.350\nMC,90.000,0.400\nMC,100.000,0.600\nMC,100.000,0.600\nMC,100.000,0.600\nMC,100.000,0.600\nMC,120.000,0.650\nMC,175.000,0.700\nMC,180.000,0.750\nMC,199.990,0.800\nMC,200.000,0.900\nMC,200.000,0.900\nMC,550.000,0.950\nMC,899.990,1.000\nVISA,10.000,0.062\nVISA,15.000,0.188\nVISA,15.000,0.188\nVISA,20.000,0.250\nVISA,25.000,0.312\nVISA,49.990,0.375\nVISA,74.990,0.438\nVISA,80.000,0.500\nVISA,99.990,0.625\nVISA,99.990,0.625\nVISA,125.670,0.688\nVISA,200.000,0.750\nVISA,250.000,0.875\nVISA,250.000,0.875\nVISA,299.000,0.938\nVISA,300.000,1.000\n",
                        "artifact_description": "Table showing the distribution of transaction amounts based on card type, including AMEX, DISC, MC, and VISA.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/123/report_84/q3.png",
                        "artifact_description": "Violin plot illustrating the distribution of transaction amounts for different card types: AMEX, DISC, MC, and VISA.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT cc.card_type_code, ft.transaction_amount, CUME_DIST () OVER (PARTITION BY cc.card_type_code ORDER BY ft.transaction_amount) AS distribution FROM financial_transactions AS ft JOIN customers_cards AS cc ON ft.card_id = cc.card_id ORDER BY cc.card_type_code, ft.transaction_amount;",
                    "chart_fn_params": {
                        "name": "catplot",
                        "parameters": {
                            "kind": "violin",
                            "x": "card_type_code",
                            "y": "transaction_amount",
                            "hue": None,
                            "col": None,
                            "row": None,
                        },
                    },
                },
                "title": "Distribution of Transaction Amounts by Card Type",
                "summary": "The analysis reveals that transaction amounts vary significantly across different card types. MC transactions show the widest range, with amounts reaching up to 899.99, while AMEX and DISC have narrower distributions. VISA transactions also display a broad range, with a maximum of 300.00. This suggests that MC and VISA are used for higher-value transactions more frequently than AMEX and DISC.",
            },
        ],
    },
}


async def main():
    await asyncio.create_task(
        optimize(
            api_key="456",
            username="text",
            report_id="",
            task_type="optimization",
            inputs=x["inputs"],
            outputs=x["outputs"],
        )
    )


if __name__ == "__main__":
    asyncio.run(main())


"""
Sample curl:
curl --location '0.0.0.0:1234/gen_optimization_task' \
--header 'Content-Type: application/json' \
--data '{
    "question": "suggest me restaurants for an outing. I want a variety of cuisines and at least 5 restaurants visited",
    "api_key": "456",
    "report_id": "",
    "task_type": "optimization",
    "gather_context": {
        "problem_statement": "Determine the optimal locations for purchasing condominiums in Singapore based on customer preferences and financial capabilities.",
        "context": "",
        "objective": "Maximize the potential return on investment from property purchases by analyzing financial transactions to assess customer spending patterns and preferences. This will involve aggregating transaction amounts from the financial_transactions table, filtered by transaction types that indicate property-related expenses.",
        "constraints": [],
        "variables": ["property_id", "location", "price", "customer_id"],
        "issues": [
            "The current database schema does not include specific information about properties, such as their locations, prices, or types (e.g., condos). Additional data sources are needed to provide insights into available condominiums in Singapore."
        ],
    },
    "explore": [
        {
            "qn_id": 0,
            "generated_qn": "How do the financial capabilities of customers vary over time based on their transaction amounts?",
            "independent_variable": {
                "name": "transaction_date",
                "description": "Date of the financial transaction.",
                "table.column": ["financial_transactions.transaction_date"],
            },
            "artifacts": {
                "table_csv": {
                    "artifact_content": "customer_id,customer_first_name,customer_last_name,transaction_date,transaction_amount,cumulative_transaction_amount\n1,John,Doe,2020-01-05,99.990,99.990\n1,John,Doe,2020-02-15,15.000,114.990\n1,John,Doe,2020-03-20,200.000,314.990\n1,John,Doe,2020-04-14,175.000,489.990\n1,John,Doe,2022-01-08,250.000,739.990\n1,John,Doe,2022-02-18,200.000,939.990\n1,John,Doe,2022-03-27,120.000,1059.990\n1,John,Doe,2022-04-15,20.000,1079.990\n1,John,Doe,2023-01-01,49.990,1129.980\n1,John,Doe,2023-02-04,10.000,1139.980\n1,John,Doe,2023-02-14,125.670,1265.650\n1,John,Doe,2023-02-15,20.000,1285.650\n1,John,Doe,2023-03-22,150.000,1435.650\n1,John,Doe,2023-04-09,125.000,1560.650\n1,John,Doe,2024-01-23,74.990,1635.640\n1,John,Doe,2024-02-09,25.000,1660.640\n2,Jane,Doe,2020-05-17,149.990,149.990\n2,Jane,Doe,2020-06-12,20.000,169.990\n2,Jane,Doe,2022-05-24,550.000,719.990\n2,Jane,Doe,2022-06-14,100.000,819.990\n2,Jane,Doe,2023-05-17,59.990,879.980\n2,Jane,Doe,2023-06-03,15.000,894.980\n2,Jane,Doe,2024-03-29,100.000,994.980\n2,Jane,Doe,2024-04-14,75.000,1069.980\n3,Robert,Jones,2020-07-28,100.000,100.000\n3,Robert,Jones,2020-08-05,90.000,190.000\n3,Robert,Jones,2021-01-04,35.200,225.200\n3,Robert,Jones,2021-02-11,50.000,275.200\n3,Robert,Jones,2021-03-19,299.000,574.200\n3,Robert,Jones,2021-04-07,15.000,589.200\n3,Robert,Jones,2023-07-20,99.990,689.190\n3,Robert,Jones,2023-08-12,80.000,769.190\n4,Michael,Lee,2021-05-18,180.000,180.000\n4,Michael,Lee,2021-06-30,200.000,380.000\n4,Michael,Lee,2022-07-16,300.000,680.000\n4,Michael,Lee,2022-08-06,250.000,930.000\n5,William,Chang,2021-07-27,59.990,59.990\n5,William,Chang,2021-08-03,20.000,79.990\n5,William,Chang,2021-09-14,450.000,529.990\n5,William,Chang,2021-10-05,50.000,579.990\n5,William,Chang,2022-09-18,899.990,1479.980\n5,William,Chang,2022-10-12,100.000,1579.980\n5,William,Chang,2023-09-01,199.990,1779.970\n5,William,Chang,2023-10-17,35.000,1814.970\n5,William,Chang,2024-05-05,299.990,2114.960\n5,William,Chang,2024-06-28,50.000,2164.960\n",
                    "artifact_description": "Table showing customer transaction data over time, including transaction amounts and cumulative transaction amounts for each customer.",
                },
                "image": {
                    "artifact_location": "/backend/oracle/reports/123/report_84/q0.png",
                    "artifact_description": "Line chart depicting transaction amounts over time, showing fluctuations in customer spending.",
                },
            },
            "working": {
                "generated_sql": "SELECT c.customer_id, c.customer_first_name, c.customer_last_name, ft.transaction_date, ft.transaction_amount, SUM (ft.transaction_amount) OVER (PARTITION BY c.customer_id ORDER BY ft.transaction_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_transaction_amount FROM customers AS c JOIN accounts AS a ON a.customer_id = c.customer_id JOIN financial_transactions AS ft ON ft.account_id = a.account_id;",
                "chart_fn_params": {
                    "name": "relplot",
                    "parameters": {
                        "kind": "line",
                        "x": "transaction_date",
                        "y": "transaction_amount",
                        "hue": None,
                        "col": None,
                        "row": None,
                    },
                },
            },
            "title": "Analysis of Customer Financial Transactions Over Time",
            "summary": "The data reveals varying financial capabilities among customers, with some showing consistent spending and others experiencing spikes. This information can help identify potential property buyers in Singapore, particularly for condos, by assessing their financial activity and stability over time.",
        },
        {
            "qn_id": 1,
            "generated_qn": "What are the financial capabilities of customers with different first names based on their transaction amounts?",
            "independent_variable": {
                "name": "customer_first_name",
                "description": "First name of the customer.",
                "table.column": ["customers.customer_first_name"],
            },
            "artifacts": {
                "table_csv": {
                    "artifact_content": "customer_first_name,total_transaction_amount\nWilliam,2164.960\nJohn,1660.640\nJane,1069.980\nMichael,930.000\nRobert,769.190\n",
                    "artifact_description": "Table showing total transaction amounts by customer first name.",
                },
                "image": {
                    "artifact_location": "/backend/oracle/reports/123/report_84/q1.png",
                    "artifact_description": "Bar chart displaying total transaction amounts for customers with different first names.",
                },
            },
            "working": {
                "generated_sql": "SELECT c.customer_first_name, SUM (ft.transaction_amount) AS total_transaction_amount FROM customers AS c JOIN accounts AS a ON c.customer_id = a.customer_id JOIN financial_transactions AS ft ON a.account_id = ft.account_id GROUP BY c.customer_first_name ORDER BY total_transaction_amount DESC NULLS LAST;",
                "chart_fn_params": {
                    "name": "catplot",
                    "parameters": {
                        "kind": "bar",
                        "x": "customer_first_name",
                        "y": "total_transaction_amount",
                        "hue": None,
                        "col": None,
                        "row": None,
                    },
                },
            },
            "title": "Analysis of Customer Transaction Amounts by First Name",
            "summary": "The analysis reveals that customers named William have the highest total transaction amount, followed by John and Jane. This suggests that individuals with these names may have higher financial capabilities. This insight could be useful for targeting potential property buyers in Singapore, especially for condos.",
        },
        {
            "qn_id": 2,
            "generated_qn": "How do the financial capabilities of customers vary based on their last names?",
            "independent_variable": {
                "name": "customer_last_name",
                "description": "Last name of the customer.",
                "table.column": ["customers.customer_last_name"],
            },
            "artifacts": {
                "table_csv": {
                    "artifact_content": "customer_last_name,total_transaction_amount\nDoe,2730.620\nChang,2164.960\nLee,930.000\nJones,769.190\n",
                    "artifact_description": "Table showing total transaction amounts grouped by customer last names.",
                },
                "image": {
                    "artifact_location": "/backend/oracle/reports/123/report_84/q2.png",
                    "artifact_description": "Bar chart displaying total transaction amounts for customers with last names Doe, Chang, Lee, and Jones.",
                },
            },
            "working": {
                "generated_sql": "SELECT c.customer_last_name, SUM (ft.transaction_amount) AS total_transaction_amount FROM customers AS c JOIN accounts AS a ON c.customer_id = a.customer_id JOIN financial_transactions AS ft ON a.account_id = ft.account_id GROUP BY c.customer_last_name ORDER BY total_transaction_amount DESC NULLS LAST;",
                "chart_fn_params": {
                    "name": "catplot",
                    "parameters": {
                        "kind": "bar",
                        "x": "customer_last_name",
                        "y": "total_transaction_amount",
                        "hue": None,
                        "col": None,
                        "row": None,
                    },
                },
            },
            "title": "Customer Financial Capabilities by Last Name",
            "summary": "The analysis reveals that customers with the last name 'Doe' have the highest total transaction amount, followed by 'Chang', 'Lee', and 'Jones'. This suggests varying financial capabilities among these groups, with 'Doe' being the most financially active.",
        },
        {
            "qn_id": 3,
            "generated_qn": "What is the distribution of transaction amounts based on the type of card used by customers?",
            "independent_variable": {
                "name": "card_type_code",
                "description": "Type of card used for the transaction.",
                "table.column": ["customers_cards.card_type_code"],
            },
            "artifacts": {
                "table_csv": {
                    "artifact_content": "card_type_code,transaction_amount,distribution\nAMEX,20.000,0.333\nAMEX,20.000,0.333\nAMEX,59.990,0.500\nAMEX,125.000,0.667\nAMEX,149.990,0.833\nAMEX,150.000,1.000\nDISC,50.000,0.500\nDISC,50.000,0.500\nDISC,299.990,0.750\nDISC,450.000,1.000\nMC,15.000,0.050\nMC,20.000,0.100\nMC,35.000,0.150\nMC,35.200,0.200\nMC,50.000,0.250\nMC,59.990,0.300\nMC,75.000,0.350\nMC,90.000,0.400\nMC,100.000,0.600\nMC,100.000,0.600\nMC,100.000,0.600\nMC,100.000,0.600\nMC,120.000,0.650\nMC,175.000,0.700\nMC,180.000,0.750\nMC,199.990,0.800\nMC,200.000,0.900\nMC,200.000,0.900\nMC,550.000,0.950\nMC,899.990,1.000\nVISA,10.000,0.062\nVISA,15.000,0.188\nVISA,15.000,0.188\nVISA,20.000,0.250\nVISA,25.000,0.312\nVISA,49.990,0.375\nVISA,74.990,0.438\nVISA,80.000,0.500\nVISA,99.990,0.625\nVISA,99.990,0.625\nVISA,125.670,0.688\nVISA,200.000,0.750\nVISA,250.000,0.875\nVISA,250.000,0.875\nVISA,299.000,0.938\nVISA,300.000,1.000\n",
                    "artifact_description": "Table showing the distribution of transaction amounts based on card type, including AMEX, DISC, MC, and VISA.",
                },
                "image": {
                    "artifact_location": "/backend/oracle/reports/123/report_84/q3.png",
                    "artifact_description": "Violin plot illustrating the distribution of transaction amounts for different card types: AMEX, DISC, MC, and VISA.",
                },
            },
            "working": {
                "generated_sql": "SELECT cc.card_type_code, ft.transaction_amount, CUME_DIST () OVER (PARTITION BY cc.card_type_code ORDER BY ft.transaction_amount) AS distribution FROM financial_transactions AS ft JOIN customers_cards AS cc ON ft.card_id = cc.card_id ORDER BY cc.card_type_code, ft.transaction_amount;",
                "chart_fn_params": {
                    "name": "catplot",
                    "parameters": {
                        "kind": "violin",
                        "x": "card_type_code",
                        "y": "transaction_amount",
                        "hue": None,
                        "col": None,
                        "row": None,
                    },
                },
            },
            "title": "Distribution of Transaction Amounts by Card Type",
            "summary": "The analysis reveals that transaction amounts vary significantly across different card types. MC transactions show the widest range, with amounts reaching up to 899.99, while AMEX and DISC have narrower distributions. VISA transactions also display a broad range, with a maximum of 300.00. This suggests that MC and VISA are used for higher-value transactions more frequently than AMEX and DISC.",
        },
    ],
}'
"""
