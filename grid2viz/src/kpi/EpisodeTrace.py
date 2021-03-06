from . import observation_model
from .env_actions import env_actions
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

#colors for production share sunburst pie
dic_colors_prod_types={'nuclear': 'darkgoldenrod', 'thermal': 'coral', 'wind': 'darkgreen', 'solar': 'gold', 'hydro':'steelblue'}
##WARNING: make sure the "light" color equivalent exists or override it with another "light" color name
dic_light_colors_prod_types={k: 'light'+v for k,v in dic_colors_prod_types.items()}
dic_light_colors_prod_types['nuclear']='goldenrod'
dic_light_colors_prod_types['wind']='green'
dic_light_colors_prod_types['solar']='palegoldenrod'

def get_total_overflow_trace(episode_analytics, episode_data):
    df = get_total_overflow_ts(episode_analytics, episode_data)
    return [go.Scatter(
        x=df["time"],
        y=df["value"],
        name="Nb of overflows"
    )]


def get_total_overflow_ts(episode_analytics, episode_data):
    df = pd.DataFrame(index=episode_analytics.timesteps,
                      columns=["time", "value","line_ids"])
    for (time_step, obs) in enumerate(episode_data.observations):
        # TODO: observations length and timsteps length should match
        try:
            tstamp = episode_analytics.timestamps[time_step]
            ov = obs.timestep_overflow
            overflows=[i for i in range(len(ov)) if ov[i]==1]
            df.loc[time_step, :] = [tstamp, (ov > 0).sum(),overflows]
        except:
            pass
    return df


def get_prod_share_trace(episode):
    prod_types = episode.get_prod_types()
    prod_type_values = list(prod_types.values()) if len(
        prod_types.values()) > 0 else []

    share_prod = observation_model.get_prod(episode)
    df = share_prod.groupby("equipment_name")["value"].sum()
    unique_prod_types = np.unique(prod_type_values)

    labels = [*df.index.values, *np.unique(prod_type_values)]

    parents = [prod_types.get(name) for name in df.index.values]
    #labelTypes=[l if l in dic_colors_prod_types.keys() else prod_types.get(l) for l in labels]
    colors=[dic_colors_prod_types[l] if l in dic_colors_prod_types.keys()
            else dic_light_colors_prod_types[prod_types.get(l)] for l in labels]
    values = list(df)

    for prod_type in unique_prod_types:
        parents.append("")
        value = 0
        for gen in df.index.values:
            if prod_types.get(gen) == prod_type:
                value = value + df.get(gen)
        values.append(value)

    return     [go.Sunburst(labels=labels, values=values,
                        parents=parents, branchvalues="total", marker = dict(colors=colors,
        colorscale='RdBu'))]


def get_hazard_trace(episode, equipments=None):
    ts_hazards_by_line = env_actions(
        episode, which="hazards", kind="ts", aggr=False)

    if ts_hazards_by_line.empty:
        return []

    if 'total' in equipments:
        ts_hazards_by_line = ts_hazards_by_line.assign(
            total=episode.hazards.groupby('timestamp', as_index=True)[
                'value'].sum()
        )

    if equipments is not None:
        ts_hazards_by_line = ts_hazards_by_line.loc[:, equipments]

    return [go.Scatter(x=ts_hazards_by_line.index,
                       y=ts_hazards_by_line[line],
                       name=line)
            for line in ts_hazards_by_line.columns]


def get_maintenance_trace(episode, equipments=None):
    ts_maintenances_by_line = env_actions(
        episode, which="maintenances", kind="ts", aggr=False)
    
    if ts_maintenances_by_line.empty:
        return []
    
    if 'total' in equipments:
        ts_maintenances_by_line = ts_maintenances_by_line.assign(
            total=episode.maintenances.groupby(
                'timestamp', as_index=True)['value'].sum()
        )

    if equipments is not None:
        ts_maintenances_by_line = ts_maintenances_by_line.loc[:, equipments]

    return [go.Scatter(x=ts_maintenances_by_line.index,
                       y=ts_maintenances_by_line[line],
                       name=line)
            for line in ts_maintenances_by_line.columns]


def get_all_prod_trace(episode, prod_types, selection):
    prod_with_type = observation_model.get_prod(episode).assign(
        prod_type=[prod_types.get(equipment_name)
                   for equipment_name in observation_model.get_prod(episode)['equipment_name']]
    )
    prod_type_names = prod_types.values()
    trace = []
    if 'total' in selection:
        trace.append(
            go.Scatter(
                x=prod_with_type['timestamp'].unique(),
                y=prod_with_type.groupby('timestamp')['value'].sum(),
                name='total'
            )
        )
    for name in prod_type_names:
        if name in selection:
            trace.append(go.Scatter(
                x=prod_with_type[prod_with_type.prod_type.values ==
                                 name]['timestamp'].drop_duplicates(),
                y=prod_with_type[prod_with_type.prod_type.values == name].groupby(['timestamp'])[
                    'value'].sum(),
                name=name
            ))
            selection.remove(
                name)  # remove prod type from selection to avoid misunderstanding in get_def_trace_per_equipment()

    return [*trace, *get_df_trace_per_equipment(observation_model.get_prod(episode, selection))]


def get_load_trace_per_equipment(episode, equipements):
    all_equipements = observation_model.get_load(episode)
    load_equipments = observation_model.get_load(episode, equipements)

    if 'total' in equipements:
        load_equipments = load_equipments.append(pd.DataFrame({
            'equipement_id': ['nan' for i in all_equipements.groupby('timestep').size()],
            'equipment_name': ['total' for i in all_equipements.groupby('timestep').size()],
            'timestamp': [timestamp for timestamp in all_equipements['timestamp'].unique()],
            'timestep': [timestep for timestep in all_equipements['timestep'].unique()],
            'value': [value for value in all_equipements.groupby('timestep')['value'].sum()]
        }))

    return get_df_trace_per_equipment(load_equipments)


def get_usage_rate_trace(episode):
    df = observation_model.get_usage_rate(episode)
    line = {
        "shape": "spline",
        "width": 0,
        "smoothing": 1
    }
    trace = [
        go.Scatter(
            x=df["timestamp"],
            y=df["value"]["quantile10"],
            name="quantile 10",
            line=line
        ), go.Scatter(
            x=df["timestamp"],
            y=df["value"]["quantile25"],
            name="quantile 25",
            fill="tonexty",
            fillcolor="rgba(159, 197, 232, 0.63)",
            line=line
        ), go.Scatter(
            x=df["timestamp"],
            y=df["value"]["median"],
            name="median",
            fill="tonexty",
            fillcolor="rgba(31, 119, 180, 0.5)",
            line={
                "color": "rgb(31, 119, 180)",
                "shape": "spline",
                "smoothing": 1
            }
        ), go.Scatter(
            x=df["timestamp"],
            y=df["value"]["quantile75"],
            name="quantile 75",
            fill="tonexty",
            fillcolor="rgba(31, 119, 180, 0.5)",
            line=line
        ), go.Scatter(
            x=df["timestamp"],
            y=df["value"]["quantile90"],
            name="quantile 90",
            fill="tonexty",
            fillcolor="rgba(159, 197, 232, 0.63)",
            line=line
        ), go.Scatter(
            x=df["timestamp"],
            y=df["value"]["max"],
            name="Max",
            line={
                "shape": "spline",
                "smoothing": 1,
                "color": "rgba(255,0,0,0.5)"
            }
        )]
    return trace


def get_df_trace_per_equipment(df):
    return [go.Scatter(
        x=df.loc[df["equipment_name"] == equipment, :]["timestamp"],
        y=df.loc[df["equipment_name"] == equipment, :]["value"],
        name=equipment
    ) for equipment in df["equipment_name"].drop_duplicates()]


def get_df_rewards_trace(episode):
    df = observation_model.get_df_computed_reward(episode)
    return [
        go.Scatter(x=df["timestep"], y=df["rewards"],
                   name=episode.agent + "_reward"),
        go.Scatter(x=df["timestep"], y=df["cum_rewards"],
                   name=episode.agent + "cum_rewards", yaxis='y2')
    ]


def get_attacks_trace(episode):
    df = episode.attacks_data_table
    return [
        go.Scatter(x=df["timestamp"], y=df["attack"].astype(int), name=episode.agent + "_attacks")
    ]
