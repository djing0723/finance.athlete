To run this webpage, first, the user will need to provide an IEX key and Finnhub key, both of which are available for free online. The user will pass these through the terminal via export API_KEY_FINNHUB= and export API_KEY_IEX=.
Once the user has provided the keys, they will change their directory to the finance folder, and then execute flask run.
The user will be greeted with a register page. Here, the user will register a username, password, confirm their password, and also input an approximate portfolio value which they can change later. The username must be a unique username not already on the website.

Once the user registers, they will be taken to the login page. They will log in, and then they will be taken to the index page, which should first be blank. To start inputting positions, the user should click the tradelog text on the top to then be redirected to the tradelog page.

In tradelog, you can update your orders according to how they were executed by your broker.
Input the ticker, indicate whether you are buying the stock or selling it, indicate the quantity, indicate if you are adding any cash (positive value) or taking out any cash (indicated by negative value), the price that you got executed at for that order, and the style that this stock represents to you (can be any value).
If the ticker you inputted is valid, it should show up in the table below indicating each order. If there is something you need to edit, click edit. On the edit tab, each box should tell you how you filled out your previous trade. Make the adjustments (you will need to fill out all the forms), and then click submit. To delete a trade, edit the previous trade such that the quantity is 0. If your portfolio value on the website does not match the actual, you can use the cash inflow/outflow to adjust your cash balance for each trade.

In index (Finance 2.0 on the nav bar), you get a view of your portfolio. You get a view of your portfolio movement, amount you have in cash, and amount you have in equity. You also can see how the markets are performing as well. In order to make the website more efficient, the website is updated three times a day: once in the morning, once in the afternoon, and once before closing. You can see when the positions have last been updated, and you are also given the option of forcing a price update.
Below, you get a view of all your positions. If your stock is has a price change greater than .5% or less than .5%, it will color green or red accordingly. You can also see your cost basis, as well as your total return. If you click any one of these companies, you can get a more detailed view of each company.
Below the positions table, once you update the positions through tradelog, you can see pie charts breaking down asset allocation. It graphs these by company, finnhub defined industries, and user defined style.
On the very bottom, there is a table showing previous earnings and future earnings. This table will show earnings that have happened up to two weeks ago for companies you own, and it also shows earnings that will happen for your companies in two weeks. You can click each stock's ticker here to get a more detailed look at the company.

Lookup will give you powerful insights into individual stocks. If you type in a supported ticker, you will be greeted with an interactive chart, company fundamental financials, target price (analyst low, median, mean, high), and news about the company
The chart will let you chart technicals and also give you an overview of the company, such as the company's financial statements. You can also draw on the chart.
Basic financials include 3 year revenue growth, 1 year revenue growth, company margins, debt/equity, average volume, and trading range. Below that, you can see what analysts are projecting for the stock.
Finally, news for the company from months ago will be shown from a variety of sources. If you click read more from ... you will be redirected to that website.
On the very bottom, click any of those logos to read more about these stocks on different websites.

The markets tab will give you more detailed about what's going on in the financial markets. The first chart gives information about the broad inidices, commmodities, bond, and select forex pairs.The second chart gives insight into the most active stocks, as well as the highest gainers and losers. Finally, news for the the broader economy is given at the bottom. Clicking "Read full article from ___" will direct you to the full article.

Last but not least, watchlist will give you tools to monitor stocks that you are interested in. By default, you are assigned a default watchlist. You cannot delete this watchlist. To add stocks, click add stock and then input a valid ticker. You will see an updated table with the ticker and chart. If you click the table or chart, you will be redirected to the stock's individual lookup page. If you click delete, the stock will be deleted from that watchlist. If you click add watchlist, you can create a blank watchlist. If you click delete watchlist, you will delete your current watchlist altogether.

https://youtu.be/VFhhWxFUGxQ