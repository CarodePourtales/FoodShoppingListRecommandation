from selenium import webdriver
import re
from selenium.webdriver.common.keys import Keys
from collections import Counter
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as wait
import operator
import nltk
import pickle

class Ingredient :
     
    def __init__(self, name, quantity) :
        self.name = name
        self.quantity = quantity
    
    def set_quantity (self, qty) :
        self.quantity = qty
    
    def add_quantity (self , quantity) :
        self.quantity += quantity
        
    def equals (self, ing) :
        if (self.name.strip().lower() == ing.name.strip().lower()) :
            return True
        else :
            return False
        
    def __str__(self) :
        return self.name + ' : ' + str(self.quantity)
    
class Recipe :
    
    def __init__(self, name, ingredients, time, vegan, vegetarian, author, mark) :
        self.name = name
        self.ingredients = ingredients
        self.time = time
        self.vegan = vegan
        self.vegetarian = vegetarian
        self.author = author
        self.mark = mark
    
    def __str__(self):
        return self.name
            
    
class User :
    
    def __init__(self, fridge, vegan, vegetarian):
        self.fridge = fridge
        self.recipes_history = []
        self.shop_list = []
        self.vegan = vegan
        self.vegetarian = vegetarian
        
    def quantity_in_fridge (self, ingredient) :
        """
        Parameters  :
        -------------
        string : ingredient

        Returns :
        -------------
        float : the quantity in the fridge
        """
        found = False
        for ing in self.fridge :
            if ing.equals(ingredient) :
                found = True
                return ing.quantity
            
        if found == False :
            return 0
    
    def add_ingredient_to_shop_list (self, ingredient) :
        """
        Adds the ingredient to the shop list, looking at the fridge to adjust quantities
        
        Parameters  :
        -------------
        string : ingredient

        Returns :
        -------------
        """
        found = False
        qty_available = self.quantity_in_fridge (ingredient)
        for ing in self.shop_list :
            if ing.equals(ingredient) :
                qty_needed = ingredient.quantity - qty_available
                ing.add_quantity (qty_needed)
                found = True
        if found == False :
            ingredient.set_quantity(ingredient.quantity - qty_available)
            self.shop_list.append(ingredient)

            
    def has_enough(self,ingredient) :
        """
        Parameters  :
        -------------
        string : ingredient

        Returns :
        -------------
        boolean : if the fridge contains enough of the ingredient for the recipe
        """
        qty_needed = ingredient.quantity
        qty_available = self.quantity_in_fridge(ingredient)
        if qty_available < qty_needed :
            return False 
        else :
            return True
    
    def update_fridge (self,ingredient) :
        """
        Updating the quantities in the fridge of the ingredient
        
        Parameters  :
        -------------
        string : ingredient

        Returns :
        -------------    
        """
        for ing in self.fridge :
            if ing.equals(ingredient) :
                qty_used = min(ing.quantity,ingredient.quantity)
                ing.set_quantity(ing.quantity - qty_used) 
        
    def __str__(self):
        return self.shop_list
        



def convert_time (string_time) :
    """
    Parameters  :
    -------------
    string : a time in hours or minutes
    
    Returns :
    -------------
    int : time in minutes
    """
    if re.search('m',string_time) : 
        time = re.search(r"(\d+)(\.)*(\d*)",string_time).group(0)
        
    else : 
        time = re.search(r"(\d+)(\.)*(\d*)",string_time).group(0)
        
    return float(time)


def convert_qty (qty,unit,ing) :
    """
    From the string of the quantity and the unit, it uses the density table to convert to grammes
    
    Parameters  :
    -------------
    string : a quantity
    string : the unit used (teaspoon, cup, unity ...)
    
    Returns :
    -------------
    float : the quantity needed 
    """
    portion_presence = False
    try :
        div = re.search(r"[^ \w]", qty).start()
        portion = float(qty[div-1]) / float(qty[div+1])
        qty_float=portion
        portion_presence = True
        qty = qty[:div-1]
    except :
        try : 
            qty_float = float(qty)
        except :
            qty_float = 10

    if portion_presence == True :
        if len(qty) > 0 :
            qty_float += float(qty[:div-2])
        
    #use the unit to have in ml
    #qty_float*=conversion_unit[unit]
    
    #convert in grammes with the database of density
    #qty_float*=density[ing]
    
    return qty_float



def create_tagged_dataset (data,tagged_dataset_path) :
    """
    From a file containing ingredients and units, builds a training set for tagging
    
    Parameters  :
    -------------
    string : the path to the dataset
    
    Returns :
    -------------
    """
    tagged = []
    dataset = open(data, "r")
    for row in dataset :
        try : 
            row = row.split(',')
            sent = []
            sent.append((row[2],'NAME'))
            sent.append((row[5],'UNIT'))
            sent.append((row[6],'OTHER'))
            tagged.append(sent)
        except :
            pass
    dataset.close()
    
    tagged_dataset = open(tagged_dataset_path, "wb")
    pickle.dump(tagged, tagged_dataset)
    tagged_dataset.close()
    


def tagging (tagged_dataset, sentence) :
    """
    Tags a sentence containing comments, one ingredient and one unit
    
    Parameters  :
    -------------
    string : the path to the tagged_dataset
    string : the string containing the ingredient 
    
    Returns :
    -------------
    string : a tagged sentence 
    """
    tagged = open(tagged_dataset, "rb")
    tagged_ingredients = pickle.load(tagged)

    back = nltk.DefaultTagger('COMMENT')
    unigram_tagger = nltk.UnigramTagger(tagged_ingredients,backoff=back)
    bigram_tagger = nltk.BigramTagger(tagged_ingredients, backoff=unigram_tagger)
    tagged_ing = unigram_tagger.tag(sentence)
    
    return tagged_ing



def extract_name_ingredient (tagged_dataset, ingredient) :
    """
    Parameters  :
    -------------
    string : a ingredient with comments
    
    Returns :
    -------------
    string : only the ingredient
    string : unit of mesure
    
    It uses tagging to extract the name and the unit and delete comments 
    """
    
    sentence = ingredient.split()
    tags = tagging (tagged_dataset, sentence)
    
    ing  = ''
    unit = ''
    
    for (word,tag) in tags :
        if tag == 'NAME' and not (word in ing) :
            ing += ' ' + word.lower().strip()
        if tag == 'UNIT' and not (word in ing) :
            unit += word.lower().strip()
            
    return ing,unit



def extract_ingredients(tagged_dataset, driver):
    """
    Parameters  :
    -------------
    driver 
    
    Returns :
    -------------
    list : the list of html text of ingredients 
    """
    
    ingredients_list = []
    ing_ul = driver.find_elements_by_xpath('//*[@id="__layout"]/div/div/div/div/div[10]/div[2]/div[1]/ul/li')
    if (len(ing_ul)==0) :
        ing_ul = driver.find_elements_by_xpath('//*[@id="__layout"]/div/div/div/div/div[11]/div[2]/div[1]/ul/li')
    for ing_li in ing_ul :
        
        ingredient_parts = ing_li.find_elements_by_class_name("recipe-ingredients__ingredient-parts")
        ingredient = ''
        for k in ingredient_parts :
            ingredient+=k.text + ' '
        name,unit = extract_name_ingredient(tagged_dataset, ingredient)
        
        qty = ing_li.find_elements_by_class_name("recipe-ingredients__ingredient-quantity")
        ingredient_qty = ''
        for k in qty :
            ingredient_qty+=k.text + ' ' 
        ingredient_qty = convert_qty (ingredient_qty,unit,name)
        
        ingredients_list.append(Ingredient(name,ingredient_qty))
        
    return ingredients_list


def get_access_recipes(path, tagged_dataset, user, meal) :
    """
    Parameters  :
    -------------
    user : the user
    string : a meal
    
    Returns :
    -------------
    string : the url of the best recipe
    """
    
    #in order to disable opening a window
    options = Options() 
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(executable_path=path, chrome_options=options)
    meal_search = meal.replace(' ', '+')
    url = 'https://www.food.com/search/' +meal_search
    driver.get(url)
    
    #vegan filter
    vegan_recipe = False
    if user.vegan == True :
        try :
            wait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//span[text()='vegan']"))).click()   
            vegan_recipe = True
        except :
            pass
        
        
    #vegetarian filter
    vegetarian_recipe = False
    if user.vegetarian == True :
        try :
            wait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//span[text()='vegetarian']"))).click()
            vegetarian_recipe = True
        except : 
            pass
    
#get best recipe
    recipes={}
    try :
        nb_recipes = wait(driver, 15).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="searchModuleTitle"]')))
        nb_recipes = nb_recipes.text
        nb_recipes = re.search(r"(\d+)(\,)*(\d*)",nb_recipes).group(0)
        comma= re.search(",*", nb_recipes)
        nb_recipes = int(nb_recipes[:comma.start()] + nb_recipes[comma.end():])
    except :
        nb_recipes = 0
    
    #for index in range (1,nb_recipes) :
    for index in range (1,10) :

        try : 
            el = wait(driver, 15).until(EC.visibility_of_element_located((By.XPATH,'//*[@id="gk-menu-search"]/div[1]/div[2]/div/div/div['+str(index)+']/div/div[2]/div/h2/a')))
        except :
            print(index)

        style_note = driver.find_element_by_xpath('//*[@id="gk-menu-search"]/div[1]/div[2]/div/div/div['+str(index)+']/div/div[2]/div/div/div[2]/div[1]/div/span').get_attribute("style")        
        start = re.search('width: ',style_note).end()
        end = re.search('%;',style_note).start()
        grade = float(style_note[start:end])
        
        time_string = driver.find_element_by_xpath('//*[@id="gk-menu-search"]/div[1]/div[2]/div/div/div['+str(index)+']/div/div[2]/div/div/div[2]/div[2]')
        time = convert_time(time_string.text)
        
        author = driver.find_element_by_xpath( '//*[@id="gk-menu-search"]/div[1]/div[2]/div/div/div['+str(index)+']/div/div[2]/div/div/div[1]/span/a').text
       
        recipes[el.get_attribute("href")] = grade

    #go the the best : 
    url = max(recipes.items(), key=operator.itemgetter(1))[0]
    #go to the recipe
    driver.get(url)
    #click 'view full recipe'
    wait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='__layout']/div/div/div/div/div/div[2]/a"))).click()
   
    #ingredients extraction
    ings = extract_ingredients(tagged_dataset, driver)
    
    #add the recipe to the user history
    recipe = Recipe (meal, ings, time, vegan_recipe, vegetarian_recipe, author, grade)
    user.recipes_history.append(recipe)
    
    #constructs the shop list / fridge of the user to add the ings
    #for all the ings
    for ing in ings :
        #if not the qty in the fridge + shop list is enough :
        if not user.has_enough(ing) :
            #add the quantity needed to the shop list 
            user.add_ingredient_to_shop_list(ing)
        #remove the quantity used for the recipe from the fridge
        user.update_fridge (ing)

    driver.quit()


if __name__ == '__main__' :
    #density = {}
    #conversion_unit = {'teaspoon' : 2, 'teaspoons' : 2, 'cup' : 250,'cups' : 250}
    path = input("Path to chrome driver : ")
    data = input("Location of the NYT data :" )
    tagged_dataset_path = input("Location of the tagged data set which is going to be created : ")
    create_tagged_dataset (data,tagged_dataset_path)
    user = User([Ingredient('sugar',100),Ingredient('flour',100)],True,True)
    
    recipe_name = input('What meal are you looking for ? : ')
    get_access_recipes(path, tagged_dataset_path, user, recipe_name)
    
    #recipe_name = input('What meal are you looking for ? : ')
    #get_access_recipes(path, tagged_dataset_path, user, recipe_name)
    
    
    print("Shopping list : ")
    print(*user.shop_list, sep="\n")
    
    print("Fridge : ")
    print(*user.fridge, sep="\n")
    

######
#Evaluation of the model : can't work because of uncleaned dataset
######
tagged_dataset = input("Location of the tagged data set which is going to be created : ")
tagged = open(tagged_dataset, "rb")
tagged_ingredients = pickle.load(tagged)

train_set = tagged_ingredients[:len(tagged_ingredients)]
test_set = tagged_ingredients[len(tagged_ingredients):]

back = nltk.DefaultTagger('OTHER')
unigram_tagger = nltk.UnigramTagger(train_set,backoff=back)
bigram_tagger = nltk.BigramTagger(train_set, backoff=unigram_tagger)

#Problem on the dataset 
#unigram_tagger.evaluate(test_set)

