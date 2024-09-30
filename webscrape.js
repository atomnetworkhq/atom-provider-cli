import axios from 'axios';
import { errorMonitor } from 'events';
import * as cheerio from 'cheerio';

async function scrapeWebsite(url) {
    console.log(url)
  try {
    return 'temp';
    const { data } = await axios.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
      },
    });
    // console.log(data)
    return data;
  } catch (error) {
    console.error('Error scraping the website:', error.message);
    throw error;
  }
}

async function scrapeForSEO( search_term){
  
  try{

    const data = await scrapeWebsite(`https://www.google.com/search?q=${encodeURIComponent(search_term)}`)
    
    const $ = cheerio.load(data);
    
    const pageTitle = $('title').text();
    console.log(`Page title: ${pageTitle}`);
    
    const items = [];
    $('a[jsname="UWckNb"]').each((index, element) => {
      const text = $(element).attr('href')
      items.push(text);
    });
      return {rankings: items,rawHTML: data};
  }
  catch(error){
    throw error;
  }

}

export { scrapeWebsite,scrapeForSEO };

