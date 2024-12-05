"use strict";
function findTag(text, tag) {
  // full match of a tag
  const fullMatchRegex = new RegExp(
    `<${tag}(\\s+[^>]*?)?>(?:[^<]|<(?!</${tag}>))*?</${tag}>|<${tag}(\\s+[^>]*?)?/>`,
    "gi"
  );

  const attributesRegex = /([\w-]+)=[\{'\"]([\s\S]+?)[\}'\"]/gi;
  // everything *inside* the tag. This doesn't include attributes
  const innerContentRegex = />([\s\S]+?)</;
  const matches = [];
  let match;

  while ((match = fullMatchRegex.exec(text)) !== null) {
    const fullText = match[0];
    // we want to find the opening tag separately, to avoid getting attributes of nested tags
    const tagOpenRegex = new RegExp(`<${tag}([\\s\\S]*?)/?>`, "gi");
    const tagOpenMatch = tagOpenRegex.exec(fullText);

    const attributes = {};
    if (tagOpenMatch) {
      let attributeMatch;
      while (
        (attributeMatch = attributesRegex.exec(tagOpenMatch[1])) !== null
      ) {
        attributes[attributeMatch[1]] = attributeMatch[2];
      }
    }

    const innerContentMatch = innerContentRegex.exec(fullText);
    const innerContent = innerContentMatch ? innerContentMatch[1] : "";
    matches.push({ fullText, attributes, innerContent: innerContent });
  }
  return matches;
}

let str =
  "# Restaurant Selection and Customer Satisfaction Executive Summary\n\nThis report analyzes the distribution of food types and customer ratings across selected restaurants in major cities. It highlights key trends in cuisine diversity and regional performance in customer satisfaction. The findings provide actionable insights to enhance restaurant offerings and strategic placement.\n\n<ORACLE-RECOMMENDATION-TITLE analysis_reference=\"1\">Enhance Cuisine Diversity</ORACLE-RECOMMENDATION-TITLE> \n\n\n\nAmerican cuisine is the most prevalent among selected restaurants, while Vegan and Mexican options are less represented [1].\n\n*Recommendation*\n- **Expand** menu offerings to include more Vegan and Mexican options.\n- **Promote** diverse food types to attract a wider customer base.\n- **Monitor** the performance of newly added cuisines.\n\n<ORACLE-RECOMMENDATION-TITLE analysis_reference=\"3\">Optimize Geographic Distribution</ORACLE-RECOMMENDATION-TITLE> \n\n\n\nLos Angeles, New York, and San Francisco each have three restaurants with average ratings between **4.13** and **4.30**, while Miami has two restaurants with the highest average rating of **4.50** [3].\n\n*Recommendation*\n- **Increase** presence in high-performing regions like Miami.\n- **Assess** market potential in existing cities to identify growth opportunities.\n- **Balance** restaurant distribution to maximize coverage and ratings.\n\n<ORACLE-RECOMMENDATION-TITLE analysis_reference=\"4\">Maintain High Customer Satisfaction</ORACLE-RECOMMENDATION-TITLE> \n\n\n\nA majority of selected restaurants fall within the **4-5** rating range with an average rating of **4.425**, indicating strong customer satisfaction [4].\n\n*Recommendation*\n- **Implement** quality control measures to sustain high ratings.\n- **Gather** customer feedback regularly to identify improvement areas.\n- **Reward** high-performing restaurants to encourage excellence.\n\n\n\n# Optimizing Restaurant Selection for Diverse Culinary Outings\n\n## Problem Statement\n\nOrganizations and individuals often seek to curate memorable dining experiences by visiting multiple restaurants that offer a variety of cuisines. The primary challenge lies in selecting at least five restaurants that each provide different types of food, ensuring a diverse and enriching culinary outing. This optimization problem not only enhances the dining experience but also accommodates varied taste preferences, making the selection process both strategic and satisfying.\n\n## Context\n\nTo address this problem, the following database schema is available:\n\n```sql\nCREATE TABLE geographic (\n  city_name text,\n  county text,\n  region text\n);\nCREATE TABLE location (\n  restaurant_id bigint,\n  house_number bigint,\n  street_name text,\n  city_name text\n);\nCREATE TABLE restaurant (\n  id bigint,\n  name text,\n  food_type text,\n  city_name text,\n  rating real\n);\n```\n\nThese tables provide comprehensive information about restaurants, including their locations, types of cuisine, and ratings. Utilizing this data, we can identify and select restaurants that not only offer diverse food types but also meet specific location and quality criteria. This structured approach ensures that the selected restaurants align with the desired variety and meet the requirements for an optimal dining outing.\n\n\n## Data Exploration\n### Distribution of Food Types Offered by Selected Restaurants\nIn this section, we analyze the distribution of food types offered by the selected restaurants to identify the variety and prevalence of different cuisines. This examination reveals that American cuisine is the most commonly offered, while Vegan and Mexican options are less prevalent. Understanding these distributions is essential for selecting restaurants that meet the diversity constraints of our selection criteria.\n<MultiTable><Table type={fetched_table_csv} csv={Food Type,Number of Restaurants\nVegan,1\nSeafood,2\nAmerican,3\nJapanese,2\nMexican,1\nItalian,2\n} /><Table type={test_table} csv={Food tttType,Number of Restaurants\nVegan,1\nSeafood,2\nAmerican,3\nJapanese,2\nMexican,1\nItalian,2\n} /></MultiTable>\n\n\nThis was generated with:\n```sql\nSELECT food_type,\n       COUNT(*) AS number_of_restaurants\nFROM restaurant\nGROUP BY food_type;\n```\n\nAmerican cuisine is the most commonly offered food type among the selected restaurants, while Vegan and Mexican options are less prevalent.\n### Distribution and Average Ratings of Selected Restaurants Across Major Cities\nIn this section, we explore the distribution of the selected restaurants across key cities, presenting the number of establishments per city alongside their average ratings. This analysis is vital for assessing regional representation and customer satisfaction, ensuring that our selected restaurants offer a diverse range of food types while maintaining high quality standards. Insights from this distribution help in making informed decisions aligned with our objective to curate a varied and exceptional restaurant portfolio.\n<MultiTable><Table type={fetched_table_csv} csv={City Name,Number of Restaurants,Average Rating\nLos Angeles,3,4.167\nNew York,3,4.3\nSan Francisco,3,4.133\nMiami,2,4.5\n} /></MultiTable>\n\n\nThis was generated with:\n```sql\nSELECT city_name,\n       COUNT(*) AS number_of_restaurants,\n       AVG(rating) AS average_rating\nFROM restaurant\nGROUP BY city_name;\n```\n\nThree cities—Los Angeles, New York, and San Francisco—each have three selected restaurants with average ratings ranging from 4.13 to 4.30, while Miami has two restaurants with the highest average rating of 4.50, suggesting a higher customer satisfaction in Miami despite having fewer establishments.\n### Restaurant Ratings Distribution and Averages\nIn this section, we analyze the ratings of the selected restaurants across different rating ranges, detailing the number of establishments in each range and their average ratings. This distribution provides valuable insights into customer satisfaction and the overall quality of the restaurants, supporting the selection of diverse and highly-rated establishments as outlined in the problem statement.\n<MultiTable><Table type={fetched_table_csv} csv={Rating Range,Number of Restaurants,Average Rating\n4-5,8,4.425\n3-4,3,3.8\n} /></MultiTable>\n\n\nThis was generated with:\n```sql\nSELECT CASE\n           WHEN rating >= 0\n                AND rating < 1 THEN '0-1'\n           WHEN rating >= 1\n                AND rating < 2 THEN '1-2'\n           WHEN rating >= 2\n                AND rating < 3 THEN '2-3'\n           WHEN rating >= 3\n                AND rating < 4 THEN '3-4'\n           WHEN rating >= 4\n                AND rating <= 5 THEN '4-5'\n           ELSE 'Unknown'\n       END AS rating_range,\n       COUNT(*) AS number_of_restaurants,\n       AVG(rating) AS average_rating\nFROM restaurant\nGROUP BY<Image path={backend/server/test.png} /> rating_range\nORDER BY rating_range;\n```\n\nA majority of the selected restaurants fall within the higher rating range of 4-5, indicating strong customer satisfaction. Additionally, the average rating in the 4-5 range is significantly higher than in the 3-4 range, highlighting better performance among these establishments.\n\n## Recommendations\n\n1. Explore local food blogs or restaurant review sites to find a diverse selection of restaurants in your area.<br />\n2. Consider visiting a food festival or market where multiple food vendors offer different cuisines.<br />\n3. Use restaurant discovery apps to filter by food type and find highly rated options.<br />\n4. Ask friends or family for recommendations based on their experiences with various cuisines.<br />\n5. Check social media platforms for trending restaurants that offer a variety of food types.\n";

const tables = findTag(str, "table");

// replace tables with oracle-tables
for (const table of tables) {
  const id = crypto.randomUUID();
  str = str.replace(table.fullText, `<oracle-table id="${id}"></oracle-table>`);
  tables[id] = { columns: [] };
}

// find multi tables
const multitables = findTag(str, "multitable");

// replace multitables with oracle-multitables
for (const multitable of multitables) {
  const id = crypto.randomUUID();
  //   find table ids
  const tables = findTag(multitable.fullText, "oracle-table");

  str = str.replace(
    multitable.fullText,
    `<oracle-multitable id="${id}"></oracle-multitable>`
  );

  multitables[id] = { tableIds: tables.map((t) => t.attributes.id) };
}

// parse images
const images = findTag(str, "image");

// replace images with oracle-images
for (const image of images) {
  const id = crypto.randomUUID();
  str = str.replace(image.fullText, `<oracle-image id="${id}"></oracle-image>`);
  images[id] = image;
}

console.log(tables);
console.log(multitables);
console.log(images);
