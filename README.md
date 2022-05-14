# companies_data
Code is not allowed to use without my consent. <br>
Demo version of a project I have developed. It should've been a live companies data checker(every day) <br>
and a charts former for telegram and web clients. <br>
Project closed. I've made only: 
- historical outstanding shares(sec,companies house,sharesoutstandinghistory,macrotrends), 
- historical institutional holdings and transactions from real documents(3 counting algorithms), 
- historical insider holdings and transactions from real documents, 
- historical cash and cash equivalents, 
- historical research and development costs, 
- finding historical prices (nasdaq, barchart, stockinvest, yahoo), 
- finding real and historical names from a name (can be incorrect), historical ticker, country, listed or not,
  exchange (was listed or is listed), cik.

First usage is long (due to getting historical data from 2013, lack of proxies(limits on data receiving servers), <br>
4 logic cpu on my mac (only 2 celery workers(1 and 2 concurrency).<br>
The code can run faster if u edit worker.py and add more workers to docker and proxies)). <br>
But if u run it after the looong first time, u'll need to collect only today's data (quick process). <br>
U also can see db writting and file writting due to a demo version. <br>
U may find errors too(sources may change and It's demo).<br>

        To run docker-compose in companies dir enter:

                docker-compose up –d -–build



            Then wait containers to load and enter:

        docker-compose exec web alembic upgrade head

            to make migrations (creating db schema)

  
