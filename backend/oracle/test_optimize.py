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
            "problem_statement": "Select a diverse set of at least 5 restaurants for an outing, ensuring a variety of cuisines is represented.",
            "context": "",
            "objective": "The key metric to optimize is the diversity of cuisines among the selected restaurants. This can be calculated by fetching data from the 'restaurant' table, grouping by 'food_type', and ensuring that at least 5 unique 'food_type' entries are included in the selection.",
            "constraints": [
                "At least 5 restaurants must be selected.",
                "The selected restaurants must represent a variety of cuisines.",
            ],
            "variables": ["restaurant_id", "food_type"],
            "issues": [],
        },
        "explore": [
            {
                "qn_id": 0,
                "generated_qn": "What are the unique food types available in the restaurant dataset?",
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "food_type\nVegan\nSeafood\nAmerican\nJapanese\nMexican\nItalian\n",
                        "artifact_description": "Table showing distinct food types available in the restaurant dataset.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/test/report_37/q0.png",
                        "artifact_description": "Bar chart displaying the count of unique food types available in the dataset, including Vegan, Seafood, American, Japanese, Mexican, and Italian.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT DISTINCT r.food_type FROM restaurant AS r;",
                    "reason_for_analysis_eval": "The analysis provides a list of unique cuisines available in the dataset, which directly addresses the user's objective of selecting a diverse set of restaurants for an outing. This insight is actionable as it allows the user to choose restaurants from different cuisines, ensuring variety. Since no previous analyses were provided, the information about the available cuisines is considered new.",
                },
                "title": "Variety of Cuisines in Restaurant Dataset",
                "summary": "The dataset reveals a diverse range of cuisines available for selection, including Vegan, Seafood, American, Japanese, Mexican, and Italian. This variety ensures a broad choice for an outing, catering to different culinary preferences.",
                "evaluation": {"analysis_usefulness": True, "analysis_newness": True},
            },
            {
                "qn_id": 3,
                "generated_qn": "What is the distribution of food types across different cities in the dataset?",
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "city_name,food_type,food_type_count\nLos Angeles,American,1\nLos Angeles,Italian,1\nLos Angeles,Japanese,1\nMiami,Seafood,2\nNew York,American,1\nNew York,Italian,1\nNew York,Japanese,1\nSan Francisco,American,1\nSan Francisco,Mexican,1\nSan Francisco,Vegan,1\n",
                        "artifact_description": "Table showing the distribution of food types across different cities, including Los Angeles, Miami, New York, and San Francisco. Key columns are city_name, food_type, and food_type_count.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/test/report_37/q3.png",
                        "artifact_description": "Bar chart displaying the count of different food types available in various cities, with each bar representing a specific food type in a city.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT r.city_name, r.food_type, COUNT (r.food_type) AS food_type_count FROM restaurant AS r GROUP BY r.city_name, r.food_type ORDER BY r.city_name, r.food_type;",
                    "reason_for_analysis_eval": "The analysis provides a breakdown of cuisines available in specific cities, which is useful for selecting a diverse set of restaurants for an outing. It offers actionable insights by identifying cities with a variety of cuisines, helping the user to plan their outing based on location. The insights are new compared to the previous analysis as it specifies the distribution of cuisines across different cities, rather than just listing the types of cuisines available.",
                },
                "title": "Distribution of Food Types Across Cities",
                "summary": "The data reveals a variety of cuisines across different cities. Los Angeles offers American, Italian, and Japanese cuisines. Miami is notable for its focus on Seafood. New York provides American, Italian, and Japanese options, while San Francisco features American, Mexican, and Vegan cuisines. This variety ensures a diverse culinary experience across these cities.",
                "evaluation": {"analysis_usefulness": True, "analysis_newness": True},
            },
            {
                "qn_id": 5,
                "generated_qn": "What are the average ratings of restaurants for each food type?",
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "food_type,average_rating\nVegan,4.600\nItalian,4.600\nSeafood,4.500\nJapanese,4.250\nMexican,4.100\nAmerican,3.800\n",
                        "artifact_description": "Table showing average ratings of restaurants grouped by food type.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/test/report_37/q5.png",
                        "artifact_description": "Bar chart displaying average ratings of restaurants for each food type.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT r.food_type, AVG (r.rating) AS average_rating FROM restaurant AS r GROUP BY r.food_type ORDER BY average_rating DESC NULLS LAST;",
                    "reason_for_analysis_eval": "The analysis provides actionable insights by highlighting the average ratings of different cuisines, which can guide the user in selecting highly-rated restaurants for their outing. It suggests Vegan, Italian, and Seafood as top choices based on ratings, which is useful for ensuring a variety of cuisines. The insights are new as they offer a deeper dive into the ratings of each cuisine, which was not covered in the previous analyses that focused on the availability of cuisines and their distribution across cities.",
                },
                "title": "Average Restaurant Ratings by Cuisine Type",
                "summary": "The analysis reveals that Vegan and Italian cuisines have the highest average ratings at 4.6, followed by Seafood at 4.5. Japanese and Mexican cuisines have ratings of 4.25 and 4.1, respectively, while American cuisine has the lowest average rating at 3.8. This suggests a variety of highly-rated options for an outing, with Vegan, Italian, and Seafood being top choices.",
                "evaluation": {"analysis_usefulness": True, "analysis_newness": True},
            },
            {
                "qn_id": 11,
                "generated_qn": "What are the average ratings of each food type in different cities?",
                "artifacts": {
                    "table_csv": {
                        "artifact_content": "food_type,city_name,average_rating\nAmerican,Los Angeles,3.800\nAmerican,New York,3.900\nAmerican,San Francisco,3.700\nItalian,Los Angeles,4.500\nItalian,New York,4.700\nJapanese,Los Angeles,4.200\nJapanese,New York,4.300\nMexican,San Francisco,4.100\nSeafood,Miami,4.500\nVegan,San Francisco,4.600\n",
                        "artifact_description": "Table showing average ratings of different food types across various cities.",
                    },
                    "image": {
                        "artifact_location": "/backend/oracle/reports/test/report_37/q11.png",
                        "artifact_description": "Bar chart displaying average ratings of food types in Los Angeles, New York, San Francisco, and Miami.",
                    },
                },
                "working": {
                    "generated_sql": "SELECT r.food_type, r.city_name, AVG (r.rating) AS average_rating FROM restaurant AS r GROUP BY r.food_type, r.city_name ORDER BY r.food_type, r.city_name;",
                    "reason_for_analysis_eval": "The analysis provides actionable insights by suggesting specific cuisines and cities with high average ratings, which directly addresses the user's objective of selecting a diverse set of restaurants for an outing. It offers a new perspective by combining city and cuisine ratings to recommend specific types of restaurants, which was not explicitly done in previous analyses. Previous analyses focused on the availability and general ratings of cuisines, but this analysis provides a more targeted recommendation by highlighting the highest-rated cuisines in specific cities.",
                },
                "title": "Average Restaurant Ratings by Cuisine and City",
                "summary": "The data reveals that Italian cuisine in New York has the highest average rating at 4.7, followed by Vegan in San Francisco at 4.6. Seafood in Miami and Italian in Los Angeles both have high ratings of 4.5. Japanese cuisine is also well-rated in both Los Angeles and New York. For a diverse culinary outing, consider visiting Italian, Japanese, Mexican, Seafood, and Vegan restaurants in these cities.",
                "evaluation": {"analysis_usefulness": True, "analysis_newness": True},
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
