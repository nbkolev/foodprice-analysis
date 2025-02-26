import csv, re, hashlib, io, base64
from datetime import datetime
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy

WHOLESALE='на едро'
RETAIL='на дребно'
LIDL='ЛИДЛ'
COOP='КООП'
BUY_SUNFLOWER='изкупни слънчоглед'



def step_interpolate_price_range(a, b):
    dates = list(sorted(set(a.keys()).union(b.keys())))
    last_a, last_b = False, False
    new_a, new_b = {}, {}
    for date in dates:
        if date in a:
            last_a = a[date]
            new_a[date] = a[date]
        elif last_a:
            new_a[date] = last_a
        if date in b:
            last_b = b[date]
            new_b[date] = b[date]
        elif last_b:
            new_b[date] = last_b

    # Remove possibly non overlapping beginning
    for date in dates:
        if date in new_a and date in new_b:
            break
        else:
            new_a.pop(date, None)
            new_b.pop(date, None)

    return new_a, new_b

# Test price, date interpolation
a = {10:1, 11:2,13:4,15:99}
b = {11:2,12:3,14:5,15:6,17:9}
a1, b1 = step_interpolate_price_range(a,b)

if (a1 != {11: 2, 12: 2, 13: 4, 14: 4, 15: 99, 17: 99} or
        b1 != {11: 2, 12: 3, 13: 3, 14: 5, 15: 6, 17: 9}):
    print("Interpolation algorithm test fails.")
    exit(1)


def get_fig_svg(fig):
    s = io.StringIO()
    fig.savefig(s, format='svg', bbox_inches='tight')
    string = s.getvalue()
    return string


def colored_string(string):
    sum = hashlib.md5(string.encode()).digest()
    r,g,b = sum[0]/2+127, sum[1]/2+127, sum[2]/2+127
    return f'<span style="background-color:rgb({r},{g},{b})">{string}</span>'


def html_list_items(name, array, color=True):
    array = sorted(list(array))
    return f'   <li><b>{name}</b>: {", ".join(map(lambda s: colored_string(s) if color else s if s else "#без пояснение", array))}</li>\n'


with open("_SELECT_prod_name_AS_product_f_name_AS_category_ceni_datefor_AS__202502131337.csv", "rt") as csvfile:
    rows = csv.reader(csvfile, delimiter=',', quotechar='"')
    next(rows, None)
    products = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    places = set()
    sale_types = defaultdict(set)
    for row in rows:
        product_name, place_with_sale_type, date, price = row


        match = re.search(r"(?P<place>(\w+\s*)+)(\((?P<sale_type>.*)\))*", place_with_sale_type).groupdict()
        place, sale_type = place_with_sale_type, ''
        if match['sale_type']:
            place, sale_type = match['place'].strip(), match['sale_type'].strip()
        places.add(place)
        date = datetime.strptime(date, '%Y-%m-%d')
        price = float(price)
        products[product_name][place][sale_type][date] = price
        sale_types[sale_type].add(product_name)



out=open("foodprice_report.html", "wt", encoding='utf8')
out.write("<html>\n")
out.write('<head><meta charset="UTF-8"></head>\n')
out.write("<body>\n")

out.write("<h2>Данни за произход</h2>\n")
out.write("<ul>\n")
out.write(html_list_items('Местоположения', places, color=False))
out.write("</ul>\n")


out.write("<h2>Възможности за съпоставимост:</h2>\n")

out.write("<ul>\n")

out.write(html_list_items('Видове пояснение на място на продажба', sale_types.keys(), color=False))

available_for_wholesale_and_retail = sale_types[WHOLESALE].intersection(sale_types['изкупни мляко'])
out.write(html_list_items('Общи между "на едро" и "на дребно"', available_for_wholesale_and_retail))

available_for_wholesale_milk = sale_types[WHOLESALE].intersection(sale_types['изкупни мляко'])
out.write(html_list_items('Общи между "на едро" и "изкупни мляко"', available_for_wholesale_milk))

available_for_wholesale_wheat = sale_types[WHOLESALE].intersection(sale_types['изкупни пшеница'])
out.write(html_list_items('Общи между "на едро" и "изкупни пшеница"', available_for_wholesale_wheat))

available_for_wholesale_pork = sale_types[WHOLESALE].intersection(sale_types['изкупни прасета'])
out.write(html_list_items('Общи между "на едро" и "изкупни прасета"', available_for_wholesale_pork))

available_for_wholesale_sunflower = sale_types[WHOLESALE].intersection(sale_types[BUY_SUNFLOWER])
out.write(html_list_items('Общи между "на едро" и "изкупни слънчоглед"', available_for_wholesale_sunflower))

retail_available_in_lidl = sale_types[RETAIL].intersection(sale_types[LIDL])
out.write(html_list_items('Общи между "на дребно" и ЛИДЛ', retail_available_in_lidl))

retail_available_in_coop = sale_types[RETAIL].intersection(sale_types[COOP])
out.write(html_list_items('Общи между "на дребно" и КООП', retail_available_in_coop))

coop_and_lidl = retail_available_in_lidl.intersection(retail_available_in_coop)
out.write(html_list_items('Общи между КООП и ЛИДЛ"', coop_and_lidl))

out.write("</ul>\n")


def plot_quotient_for_place(ax, place, product_name, sale_type_dividend, sale_type_divisor):
    in_place_quote=products[product_name][place]
    in_place_dividend, in_place_divisor = step_interpolate_price_range(in_place_quote[sale_type_dividend], in_place_quote[sale_type_divisor])
    x1, y1 = zip(*in_place_dividend.items())
    x2, y2 = zip(*in_place_divisor.items())

    if x1==x2: # assert reported dates match
        quotient=numpy.divide(y1,y2)
        ax.plot(x1, quotient, label=place)
    else:
        out.write(f'<p>Няма съвпадение в докладваните дати за "{sale_type_dividend}" и "{sale_type_dividend}" за {product_name} в {place}</p>')


def plot_quotients_for_all_places(product_name_list, sale_type_dividend, sale_type_divisor):

    for product_name in product_name_list:
        print(f"Plotting {product_name}:")
        product = products[product_name]

        fig, ax = plt.subplots()
        fig.set_size_inches(18.5, 10.5)

        for place in product.keys():
            if sale_type_divisor in product[place] and sale_type_dividend in product[place]:
                print(f"...in {place}")
                plot_quotient_for_place(plt, place, product_name, sale_type_dividend, sale_type_divisor)
            else:
                print(f"...skipping {place}")

        ax.legend()
        out.write(f'<h3>Съотношение  {sale_type_dividend} / {sale_type_divisor} за "{product_name}"</h3>'
                  f'{get_fig_svg(fig)}')
        plt.close(fig)


out.write("\n<h1>Сравнения - Едро/Дребно</h1>\n")
plot_quotients_for_all_places(available_for_wholesale_and_retail, RETAIL, WHOLESALE)


out.write("\n<h1>Сравнения - Кооперативен съюз</h1>\n")
plot_quotients_for_all_places(retail_available_in_coop,  RETAIL, COOP)


out.write("\n<h1>Слънчогледи ...</h1>\n")
plot_quotients_for_all_places(available_for_wholesale_sunflower, WHOLESALE, BUY_SUNFLOWER)
plot_quotients_for_all_places(available_for_wholesale_sunflower, WHOLESALE, COOP)
plot_quotients_for_all_places(available_for_wholesale_sunflower, COOP, BUY_SUNFLOWER)

out.write("\n<p>Програмен код и оформление от Николай Колев / 2025 CC BY</p>")
out.write("\n</body>\n</html>")
out.close()
