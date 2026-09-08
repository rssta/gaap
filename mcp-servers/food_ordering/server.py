from mcp.server.fastmcp import FastMCP
import sys
import os 
with open("arriving_path_file.txt", "r") as file:
    arriving_path = file.read()
sys.path.insert(1, arriving_path + 'agent_helpers')
import database
import random

# Overall definitions
DRINKS = {'water': 1.99, 'orange_juice': 3.99, 'coffee': 2.49}
MAINS = {'sandwich': 5.99, 'salad': 6.49, 'pasta': 8.99, 'soup': 4.99}
SIDES = {'side_salad': 3.99, 'side_soup': 3.99, 'fruit_cup': 4.99}
DESSERTS = {'cookie': 2.49, 'pie': 4.99}

# Initialize FastMCP server
mcp = FastMCP("food_order")

@mcp.tool()
async def get_menu(type_food: str) -> dict:
    """Get the menu for a type of food.

    Args:
        type_food: One of 'drink', 'main', 'side', 'dessert'
    """
    if type_food == 'drink':
        return DRINKS
    if type_food == 'main':
        return MAINS
    if type_food == 'side':
        return SIDES
    if type_food == 'dessert':
        return DESSERTS

@mcp.tool()
async def order(username: str, password: str, order_items: list) -> str:
    """Place an order for food with an account.

    Args:
        Username: string
        Password: string
        Order items: list

    Ret:
        Str: Order status sentence, including a 'success' or 'failure'
    """
    
    user_password =  database.access_data('restaurant_password')
    user_username = database.access_data('restaurant_username')
    if username != user_username or password != user_password:
        return "failure: Could not find account matching username and password."
    
    total_menu = list(DRINKS.keys()) + list(MAINS.keys()) + list(SIDES.keys()) + list(DESSERTS.keys())

    for food_item in order_items:

        if food_item not in total_menu:
            return f"failure: Cound not find order item {food_item}, order cancelled."

    database.insert_internal_data("ordered", "food_ordering", "true")
    return "success: Order completed successfully."


@mcp.tool()
async def order_status(username: str, password: str) -> str:
    """Check the status of food ordered on an account.

    Args:
        Username: string
        Password: string
        Order items: list

    Ret:
        Str: Order status sentence, including a 'success' or 'failure'
    """

    user_password = database.access_data('restaurant_password')
    user_username = database.access_data('restaurant_username')

    if username != user_username or password != user_password:
        return "failure: Could not find account matching username and password."
    
    if "true" in database.access_internal_data('ordered', 'food_ordering'):

        if random.random() > 0.5:
            database.insert_internal_data("ordered", "food_ordering", "false")

            return "success: order is completed."
            
        else:
            return "success: order is still in progress."
    else:
        return "success: order food has not been ordered."

def main():
    # Initialize and run the server

    #database.insert_internal_data("ordered", "food_ordering", "false")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
