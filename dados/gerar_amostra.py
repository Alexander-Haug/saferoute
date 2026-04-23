"""
Script para gerar um CSV de amostra com dados simulados de criminalidade em São Paulo.
Execute uma vez: python dados/gerar_amostra.py

Quando tiver o CSV real da SSP-SP, coloque-o em dados/crimes.csv e ignore este script.
"""
import random
import csv
import os

random.seed(42)

# Bairros de SP com coordenadas aproximadas e peso de criminalidade (1=baixo, 5=alto)
BAIRROS = [
    ('Centro',           -23.548, -46.636, 5),
    ('Brás',             -23.544, -46.619, 4),
    ('Mooca',            -23.552, -46.604, 3),
    ('Sé',               -23.550, -46.633, 5),
    ('Liberdade',        -23.559, -46.632, 3),
    ('Pinheiros',        -23.563, -46.682, 2),
    ('Vila Madalena',    -23.553, -46.690, 2),
    ('Lapa',             -23.524, -46.704, 3),
    ('Barra Funda',      -23.527, -46.665, 3),
    ('Santana',          -23.500, -46.627, 3),
    ('Vila Guilherme',   -23.513, -46.613, 3),
    ('Penha',            -23.527, -46.542, 4),
    ('Itaquera',         -23.536, -46.454, 4),
    ('Guaianazes',       -23.547, -46.390, 4),
    ('Capão Redondo',    -23.672, -46.759, 5),
    ('Campo Limpo',      -23.634, -46.756, 4),
    ('Santo Amaro',      -23.651, -46.710, 3),
    ('Brooklin',         -23.619, -46.694, 2),
    ('Moema',            -23.601, -46.668, 1),
    ('Itaim Bibi',       -23.587, -46.677, 2),
    ('Jardins',          -23.572, -46.662, 1),
    ('Consolação',       -23.555, -46.659, 3),
    ('Bela Vista',       -23.557, -46.644, 3),
    ('Sacomã',           -23.597, -46.590, 4),
    ('Ipiranga',         -23.590, -46.607, 3),
    ('Cidade Tiradentes',-23.597, -46.391, 5),
    ('São Miguel',       -23.491, -46.444, 5),
    ('Brasilândia',      -23.434, -46.695, 5),
    ('Casa Verde',       -23.503, -46.659, 3),
    ('Pirituba',         -23.469, -46.734, 4),
]

TIPOS_CRIME = [
    'Furto',
    'Roubo',
    'Furto de Veículo',
    'Roubo de Veículo',
    'Lesão Corporal',
    'Tráfico de Entorpecentes',
    'Homicídio',
]

PESO_TIPO = [30, 25, 15, 10, 10, 7, 3]

SAIDA = os.path.join(os.path.dirname(__file__), 'crimes.csv')

def gerar_registros(n=15000):
    registros = []
    for _ in range(n):
        bairro, lat_base, lon_base, peso = random.choices(BAIRROS, weights=[b[3] for b in BAIRROS])[0]

        # Espalha os pontos ao redor do centro do bairro
        lat = lat_base + random.gauss(0, 0.008)
        lon = lon_base + random.gauss(0, 0.008)

        tipo = random.choices(TIPOS_CRIME, weights=PESO_TIPO)[0]
        ano  = random.choice([2022, 2023, 2024])
        mes  = random.randint(1, 12)
        hora = random.choices(range(24), weights=[
            3,2,2,2,2,2,3,4,5,5,5,5,5,5,5,5,6,7,8,8,7,6,5,4
        ])[0]

        registros.append({
            'ano':              ano,
            'mes':              mes,
            'hora':             hora,
            'tipo_crime':       tipo,
            'bairro':           bairro,
            'latitude':         round(lat, 6),
            'longitude':        round(lon, 6),
            'qtd_ocorrencias':  random.choices([1, 2, 3], weights=[70, 20, 10])[0],
        })
    return registros


def main():
    registros = gerar_registros(15000)
    colunas = ['ano', 'mes', 'hora', 'tipo_crime', 'bairro', 'latitude', 'longitude', 'qtd_ocorrencias']

    with open(SAIDA, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=colunas)
        writer.writeheader()
        writer.writerows(registros)

    print(f"CSV gerado: {SAIDA} ({len(registros)} registros)")


if __name__ == '__main__':
    main()
