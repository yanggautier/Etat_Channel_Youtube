Chart.defaults.global.defaultFontFamily = 'Nunito', '-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif';
Chart.defaults.global.defaultFontColor = '#858796';
// Pie Chart Example
var ctx2 = document.getElementById("PieChart");

var PieChart2 = new Chart(ctx2, {
  type: 'pie',
  data: {
    labels: ['un', 'deux', 'trois'],
    datasets: [{
      data: [1, 2, 3],
      backgroundColor: ['#FF5733', '#FA9F00', '#F8FB00', '#9EFE00', "#FF00FB", "#FE0183", '#FF0000'],
      hoverBackgroundColor: ['#F38663', '#F5B13A', '#F3F54F', '#B8F94C', "#FB58F9", '#FB54AA', '#FF5A5A'],
      hoverBorderColor: "rgba(234, 236, 244, 1)",
    }],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    tooltips: {
      enabled: true,
      callbacks: {
        label: function (tooltipItem, data) {
          //get the concerned dataset
          var dataset = data.datasets[tooltipItem.datasetIndex];
          //calculate the total of this data set
          var sum = dataset.data.reduce((a, b) => parseInt(a, 10) + parseInt(b, 10), 0);
          //get the current items value
          var value = dataset.data[tooltipItem.index];
          var amount = data.labels[tooltipItem.index];
          return amount + ": " + Math.round(value / sum * 10000) / 100 + "%";
        }
      }
    },

    legend: {
      display: true,
      position: "bottom",
      boxWidth: 20,
      labels: {
        fontColor: "#333",
        fontSize: 14
      }
    },
    cutoutPercentage: 80,
  },
});
