import { colorHash } from "@ctfdio/ctfd-js/ui";
import { mergeObjects } from "../../objects";
import { cumulativeSum } from "../../math";
import dayjs from "dayjs";

export function getOption(mode, places, optionMerge) {
  let option = {
    backgroundColor: 'transparent',
    title: {
      left: "center",
      text: "Top 10 " + (mode === "teams" ? "Teams" : "Users"),
      textStyle: {
        color: '#fff',
        fontSize: 16,
        fontWeight: 'bold',
      },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: 'rgba(17, 17, 17, 0.95)',
      borderColor: '#333',
      borderWidth: 1,
      textStyle: {
        color: '#eee',
      },
      axisPointer: {
        type: "cross",
        lineStyle: {
          color: '#ff003c',
          opacity: 0.5,
        },
        crossStyle: {
          color: '#ff003c',
          opacity: 0.5,
        },
      },
    },
    legend: {
      type: "scroll",
      orient: "horizontal",
      align: "left",
      bottom: 35,
      data: [],
      textStyle: {
        color: '#aaa',
      },
      pageTextStyle: {
        color: '#888',
      },
      pageIconColor: '#ff003c',
      pageIconInactiveColor: '#333',
    },
    toolbox: {
      feature: {
        dataZoom: {
          yAxisIndex: "none",
        },
        saveAsImage: {},
      },
      iconStyle: {
        borderColor: '#666',
      },
      emphasis: {
        iconStyle: {
          borderColor: '#ff003c',
        },
      },
    },
    grid: {
      containLabel: true,
      top: 80,
      left: 20,
      right: 20,
      bottom: 100,
    },
    xAxis: [
      {
        type: "time",
        boundaryGap: false,
        data: [],
        axisLine: {
          lineStyle: {
            color: '#333',
          },
        },
        axisLabel: {
          color: '#888',
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: '#1a1a1a',
          },
        },
      },
    ],
    yAxis: [
      {
        type: "value",
        axisLine: {
          lineStyle: {
            color: '#333',
          },
        },
        axisLabel: {
          color: '#888',
        },
        splitLine: {
          lineStyle: {
            color: '#1a1a1a',
          },
        },
      },
    ],
    dataZoom: [
      {
        id: "dataZoomX",
        type: "slider",
        xAxisIndex: [0],
        filterMode: "filter",
        height: 20,
        top: 35,
        backgroundColor: '#111',
        borderColor: '#333',
        fillerColor: "rgba(255, 0, 60, 0.2)",
        handleStyle: {
          color: '#ff003c',
        },
        textStyle: {
          color: '#888',
        },
        dataBackground: {
          lineStyle: {
            color: '#333',
          },
          areaStyle: {
            color: '#222',
          },
        },
      },
    ],
    series: [],
  };

  const teams = Object.keys(places);
  for (let i = 0; i < teams.length; i++) {
    const team_score = [];
    const times = [];
    for (let j = 0; j < places[teams[i]]["solves"].length; j++) {
      team_score.push(places[teams[i]]["solves"][j].value);
      const date = dayjs(places[teams[i]]["solves"][j].date);
      times.push(date.toDate());
    }

    const total_scores = cumulativeSum(team_score);
    let scores = times.map(function (e, i) {
      return [e, total_scores[i]];
    });

    option.legend.data.push(places[teams[i]]["name"]);

    const data = {
      name: places[teams[i]]["name"],
      type: "line",
      smooth: true,
      lineStyle: {
        width: 2,
      },
      symbol: 'circle',
      symbolSize: 6,
      label: {
        normal: {
          position: "top",
        },
      },
      itemStyle: {
        normal: {
          color: colorHash(places[teams[i]]["name"] + places[teams[i]]["id"]),
        },
      },
      data: scores,
    };
    option.series.push(data);
  }

  if (optionMerge) {
    option = mergeObjects(option, optionMerge);
  }
  return option;
}
