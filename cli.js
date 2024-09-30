import { Command } from 'commander';
import inquirer from 'inquirer';
import axios from 'axios';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import io from "socket.io-client";
import {scrapeForSEO} from './webscrape.js';


const program = new Command();
const API_URL = 'http://atom.atomnetwork.xyz:3000/api';

// Function to open the SQLite database
async function openDatabase() {
  return open({
    filename: './sessions.db',
    driver: sqlite3.Database,
  });
}

// Function to create the users table if it doesn't exist
async function createTable(db) {
  await db.exec(`
    CREATE TABLE IF NOT EXISTS sessions (
      email TEXT UNIQUE NOT NULL,
      token TEXT NOT NULL,
      login_ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
  `);
}

program
  .version('1.0.0')
  .description('A simple CLI example')
  .option('-n, --name <type>', 'specify your name')
  .command('login')
  .description('Login with email and password')
  .action(async () => {
    const answers = await inquirer.prompt([
      {
        type: 'input',
        name: 'email',
        message: 'Enter your email:',
      },
      {
        type: 'password',
        name: 'password',
        message: 'Enter your password:',
        mask: '*',
      },
    ]);

    const user = {
      email: answers.email,
      password: answers.password,
    };

    try {
      const response = await axios.post(`${API_URL}/users/login`, user);
      console.log(response.data);
        
      if(response.status!==200){
        console.log("Login Failed. Invalid Username or Password")
        return
      }
      // Open the database and create the table
      const db = await openDatabase();
      await createTable(db);
      await db.run(
        "INSERT INTO sessions (email, token) VALUES ($email, $token) ON CONFLICT(email) DO UPDATE SET token = $token, login_ts=current_timestamp",
        {
          $email: user.email,
          $token: response.data.token
        }
      );
      
        console.log('User data stored in the local database.');
      console.log(response)
      await db.close();
    } catch (error) {
      console.error('Error during login or database operation:', error.message);
    }
    
  });

// New command to run a background process
program
  .command('run')
  .description('Run a background process')
  .action(async () => {
    console.log('Background process started...');
    const db = await openDatabase();
    const result = await db.all('select token from sessions where login_ts = (select max(login_ts) from sessions)');
    console.log(result[0].token)
    let token=undefined;
    if (result[0] ){
       token=result[0].token;
    }
    else{
        console.log("No login found!! Please login using login argument")
    }
    if(token){
  
      const socket = io('http://atom.atomnetwork.xyz:3000', {
        auth: {
          token: token
        }
      });
      socket.on('connect', () => {
        console.log('Connected to WebSocket server');
      });
      
      socket.on('disconnect', () => {
        console.log('Disconnected from server');
      });
      
      socket.on('newServiceRequest', async (data) => {
        console.log(`New Service Request Received: ${data}`);
        const responseData={service_id:data.serviceId,
          results:null,
          service_name:'',
          response_status: 'Failed'
        }
        console.log(data.service_request_details.search_term)
        switch (data.serviceName) {
          case 'SEO':
            try{
              const scrapedData= await scrapeForSEO(data.service_request_details.search_term);
              responseData.results=scrapedData;
              responseData.response_status='Success'
              responseData.service_name='SEO'
            }
            catch(error){
              console.log(error)
              console.log("Failed to scrape the data")
            }
  
            break;
          
          default:
            console.log('Unsupported service request type');
          }
          console.log("Emitting socket response",responseData);
          socket.emit('serviceResponse', responseData);
        
      });
      
      // Send message
      socket.emit('message', 'Hello WebSocket server!');
      
      
    }
  });

program.parse(process.argv);
