from pymed import PubMed
import requests
import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns


# Función para obtener el número de resultados
def get_results_count(query):
    pubmed = PubMed(tool="MyTool", email="testemails@gmail.com")
    try:
        return pubmed.getTotalResultsCount(query)
    except Exception as e:
        print(f"Error getting results for the query '{query}': {e}")
        return None
# Función para procesar una única combinación de tipos de tumor y fármacos
def process_combination(disease, drug):
        query = f"{disease} AND {drug}"
        results_count = get_results_count(query)
        return {'disease': disease, 'drug': drug, 'results': results_count}


def obtain_fda_results(api_key, drug_term):
    base_url = "https://api.fda.gov/drug/event.json"
    
    # Parámetros de búsqueda
    params = {
        'api_key': api_key,
        'search': f'"patient.drug.medicinalproduct.exact:""{drug_term}"',
        'count': "patient.reaction.reactionmeddrapt.exact"
        }

    headers = {
        'Content-Type': 'application/json',
    }

    try:
        # Realizar la llamada a la API
        response = requests.get(base_url,  params=params, headers=headers)
        response.raise_for_status()  # Verificar si hay errores en la respuesta HTTP

        # Convertir la respuesta a JSON
        data = response.json()

        # Verificar si 'results' está presente
        if 'results' in data:
            # Devolver el json resultante
            return data
        else:
            print(f"No results found for {drug_term}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error in the API call for {drug_term}: {e}")
        return None
    
def obtain_fda_results_from_list(api_key, drugs):
    
    df_results = pd.DataFrame(columns=['drug', 'term', 'count'])

    for drug in drugs[drugs.columns[0]]:
        data = obtain_fda_results(api_key,drug)
        
        # Verificar si 'results' está presente en data
        if data is not None and 'results' in data:
            # Crear un DataFrame para los resultados del farmaco actual
            df_drug = pd.DataFrame(data['results'])
            df_drug['drug'] = drug
            
            # Concatenar al DataFrame principal
            df_results = pd.concat([df_results, df_drug], ignore_index=True)
        # Añadir un tiempo de espera de 1 segundo
        time.sleep(1)

    return df_results

#Funcion de preprocesado de datos

def data_preprocessing(results_df, rows = "drug", columns = "term", cellValues = "count", num_top_events = 12):
    #Preprocesamieto del dataframe

    # Utilizamos la función pivot_table (gestiona duplicados) para convertir el DataFrame largo a uno ancho
    results_df_wide = results_df.pivot_table(index=rows, columns=columns, values=cellValues)

    #Se elimina la etiqueta farmaco como nombre de columna
    results_df_wide.columns.name = None

    #Se resetea los indices para que Tipo de tumor y los nombres de los farmacos esten al mismo nivel
    results_df_wide.reset_index(inplace=True)

    #Se extraen los 25 eventos con mayor número de resultados en la bibliografía. Independientemente del tipo de tumor 
    top_events = results_df_wide.drop(columns=[rows]).sum().sort_values(ascending=False).head(num_top_events)

    #Filtra el dataframe para quedarte solo con la columna de tipo de tumor y los farmacos con más resultados
    results_df_wide = results_df_wide[[rows] + list(top_events.index)]

    #Define el tipo de tumor como los indices del dataframe
    results_df_wide.set_index(rows, inplace=True)

    # Suma el total de resultados de los 15 fármacos para cada tipo de tumor y crea una nueva columna llamada 'TotalResultados'
    results_df_wide['TotalResults'] = results_df_wide[list(top_events.index)].sum(axis=1)

    # Ordena el DataFrame por la nueva columna 'TotalResultados' en orden descendente
    results_df_wide = results_df_wide.sort_values(by='TotalResults', ascending=False).reset_index()
    results_df_wide = results_df_wide[[rows] + list(top_events.index)]
    results_df_wide.set_index(rows, inplace=True)

    results_df = results_df_wide.infer_objects(copy=False)
    
    return results_df, top_events

def bar_plot_results(results_df_wide, top_events, num_columns = 25, xlab = 'Drugs', 
                     plot_title ='Drugs and adverse effect. Source:Faers', legend_title = 'Adverse effect'):
    # Visualizar los resultados de cada farmaco en función del tipo de tumor
    fig, ax = plt.subplots(figsize=(10, 6))

    # Configura la paleta de colores única para cada fármaco con Seaborn
    colors = sns.color_palette("Set3", n_colors=len(top_events))

    # Creamos un gráfico de barras apiladas
    results_df_wide.head(num_columns).plot(kind='bar', stacked=True, ax=ax, color = colors, width=0.8)

    # Añadimos etiquetas y título
    ax.set_xlabel(xlab, fontsize=12)
    ax.set_ylabel('Number of results', fontsize=12)
    ax.set_title(plot_title, fontsize=14)
    ax.legend(title= legend_title, bbox_to_anchor=(1.05, 1), loc='upper left')  # Colocar la leyenda a la derecha
    plt.xticks(rotation=45, ha='right')  # Rotar las etiquetas del eje x
    plt.tight_layout()  # Ajustar el diseño del gráfico
    
    return fig
    
def iterative_pubmed_search(first_list, second_list):
    # Inicializar una lista para almacenar los resultados
    results_list = []
    
    try:
        # Bucle anidado para combinar tipos de tumor y fármacos
        for first_list_element in first_list[first_list.columns[0]]:
            for second_list_element in second_list[second_list.columns[0]]:
                # Crear la consulta combinando el tipo de tumor y el fármaco
                query = f"{first_list_element} AND {second_list_element}"
                # Obtener el número de resultados
                results_count = get_results_count(query)
                # Agregar los resultados a la lista
                results_list.append({f'{first_list.columns[0]}': first_list_element, f'{second_list.columns[0]}': second_list_element, 'Results': results_count})

        # Crear un DataFrame a partir de la lista de resultados
        results_df = pd.DataFrame(results_list)
        return results_df
    except requests.exceptions.RequestException as e:
        print(f"Error in the iterative PUBMED search: {e}")
    