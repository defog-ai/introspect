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
            "problem_statement": "Select a diverse set of at least 5 restaurants for an outing, ensuring a variety of food types.",
            "context": "",
            "objective": "Maximize the diversity of food types while ensuring at least 5 restaurants are selected. The key metric to optimize is the variety of food types available. This can be calculated by fetching data from the 'restaurant' table, aggregating over the 'food_type' column to ensure a mix of different types.",
            "constraints": [
                "At least 5 restaurants must be selected.",
                "Selected restaurants must offer a variety of food types.",
            ],
            "variables": ["restaurant_id", "food_type"],
            "issues": [],
        },
        "explore": [
            {
                "qn_id": 0,
                "generated_qn": "What are the different food types available in restaurants located in each city?",
                "independent_variable": {
                    "name": "city_name",
                    "description": "City where the restaurant is located",
                    "table.column": ["restaurant.city_name"],
                },
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "city_name,food_type\nNew York,American\nNew York,Italian\nNew York,Japanese\n",
                        "artifact_description": "Table showing different food types available in restaurants located in New York.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/test/report_79/q0.png",
                        "artifact_description": "Bar chart displaying the count of restaurants offering American, Italian, and Japanese food types in New York.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT r.city_name, r.food_type FROM restaurant AS r JOIN LOCATION AS l ON r.id = l.restaurant_id WHERE l.city_name = 'New York' ORDER BY r.food_type;",
                    "chart_fn_params": {
                        "arguments": {
                            "kind": "count",
                            "x": "food_type",
                            "y": None,
                            "hue": "city_name",
                            "col": None,
                            "row": None,
                        },
                        "name": "catplot",
                    },
                },
                "title": "Variety of Food Types in New York Restaurants",
                "summary": "The data reveals that New York offers a variety of food types, including American, Italian, and Japanese cuisines. This diversity provides a range of options for dining out, ensuring a varied culinary experience.",
            },
            {
                "qn_id": 1,
                "generated_qn": "What are the ratings of restaurants categorized by different food types?",
                "independent_variable": {
                    "name": "food_type",
                    "description": "Type of food served at the restaurant",
                    "table.column": ["restaurant.food_type"],
                },
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "food_type,average_rating\nAmerican,3.800\nItalian,4.600\nJapanese,4.250\nMexican,4.100\nSeafood,4.500\nVegan,4.600\n",
                        "artifact_description": "Table showing average ratings of restaurants categorized by different food types.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/test/report_79/q1.png",
                        "artifact_description": "Bar chart displaying average ratings of restaurants for various food types including American, Italian, Japanese, Mexican, Seafood, and Vegan.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT r.food_type, AVG (r.rating) AS average_rating FROM restaurant AS r GROUP BY r.food_type ORDER BY r.food_type;",
                    "chart_fn_params": {
                        "arguments": {
                            "kind": "bar",
                            "x": "food_type",
                            "y": "average_rating",
                            "hue": None,
                            "col": None,
                            "row": None,
                        },
                        "name": "catplot",
                    },
                },
                "title": "Restaurant Ratings by Food Type",
                "summary": "The analysis reveals that Italian and Vegan restaurants have the highest average ratings at 4.6, followed closely by Seafood at 4.5. Japanese and Mexican cuisines also have strong ratings, while American cuisine has the lowest average rating at 3.8. For a diverse outing, consider visiting Italian, Vegan, Seafood, Japanese, and Mexican restaurants.",
            },
            {
                "qn_id": 2,
                "generated_qn": "How does the average rating of restaurants vary across different food types?",
                "independent_variable": {
                    "name": "rating",
                    "description": "Rating of the restaurant",
                    "table.column": ["restaurant.rating"],
                },
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "food_type,average_rating\nVegan,4.600\nItalian,4.600\nSeafood,4.500\nJapanese,4.250\nMexican,4.100\nAmerican,3.800\n",
                        "artifact_description": "Table showing average ratings of restaurants grouped by food type.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/test/report_79/q2.png",
                        "artifact_description": "Bar chart displaying the average ratings of restaurants across different food types.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT r.food_type, AVG (r.rating) AS average_rating FROM restaurant AS r GROUP BY r.food_type ORDER BY average_rating DESC NULLS LAST;",
                    "chart_fn_params": {
                        "arguments": {
                            "kind": "bar",
                            "x": "food_type",
                            "y": "average_rating",
                            "hue": None,
                            "col": None,
                            "row": None,
                        },
                        "name": "catplot",
                    },
                },
                "title": "Average Restaurant Ratings by Food Type",
                "summary": "The analysis reveals that Vegan and Italian restaurants have the highest average ratings at 4.6, followed by Seafood at 4.5. Japanese and Mexican cuisines also have strong ratings, while American food has the lowest average rating at 3.8. For a diverse outing, consider visiting restaurants offering Vegan, Italian, Seafood, Japanese, and Mexican cuisines.",
            },
        ],
    },
}


async def main():
    await asyncio.create_task(
        optimize(
            api_key="test",
            username="text",
            report_id="",
            task_type="optimization",
            inputs=x["inputs"],
            outputs=x["outputs"],
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
