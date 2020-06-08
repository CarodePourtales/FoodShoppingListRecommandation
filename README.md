# Food Shopping List Recommandation

## Introduction
Making a food shopping list can be tricky. First you should know the meals you want to cook and then you should know the ingredients you need according to the content of your fridge. However nowadays technology is everywhere and it seems it can also invite itself in our fridge because some companies are working on a camera which analyzes the ingredients inside.
So what if, with this information, you could just pick up meals and instantly build the shopping list ? Most of people go on internet to look at a recipe and see what they have to buy but this takes time since you also have to look at your fridge. It would be easier for an user to just type a meal into a console and the tool would retrieve the ingredients in the fridge, the ingredients the user needs, and compose the shopping list.
So that the combination of computer vision on a fridge and information retrieval from cooking websites could be the next tool against waste of both time and food.

Here I only worked on information retrieval part, the user should enter names of recipes in the console and the tool would retrieve the best recipe's ingredients by searching on internet thanks to a chrome driver, using regular expressions, and tagging ingredients. Then by comparison with the fridge, the algorithm would build the shopping list according to what the users needs.

## Setup

Needs a chromedriver 
Input the correct path name of the New York dataset to create the tagged dataset 
Input any path name to create the tagged dataset

## Information about the algorithm 

### Mining Webpage

Thanks to the chrome webdriver, the algorithm retrieves information by following XPath.

### Tagger 

It is a Bigram Tagger 
