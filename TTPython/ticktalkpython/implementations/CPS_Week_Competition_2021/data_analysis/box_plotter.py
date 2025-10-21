
###Pulled from stack overlof
# import matplotlib.pyplot as plt

# fig, ax = plt.subplots()
# boxes = [
#     {
#         'label' : "Male height",
#         'whislo': 162.6,    # Bottom whisker position
#         'q1'    : 170.2,    # First quartile (25th percentile)
#         'med'   : 175.7,    # Median         (50th percentile)
#         'q3'    : 180.4,    # Third quartile (75th percentile)
#         'whishi': 187.8,    # Top whisker position
#         'fliers': []        # Outliers
#     }
# ]
# ax.bxp(boxes, showfliers=False)
# ax.set_ylabel("cm")
# plt.savefig("boxplot.png")
# plt.close()

from matplotlib import pyplot as plt


def make_boxplot(boxes):
    fig, ax = plt.subplots()
    # for b in boxes:
    ax.bxp(boxes, showfliers=False)

    # plt.savefig("boxplot.png")
    ax.set_ylabel('Synchronization Latency Overhead (ms)')
    ax.set_xlabel('Synchronized Function')
    plt.xticks(rotation = 30)
    plt.title('Overhead of Time-Interval Input Synchronization')
    plt.show()
    # plt.close()


def plot_first_test_results():

    boxes = [
        {
            'label' : "CAV1 Local Fusion",
            'whislo': 0.001602272*1000,    # Bottom whisker position
            'q1'    : 0.001733275*1000,    # First quartile (25th percentile)
            'med'   : 0.001930198*1000,    # Median         (50th percentile)
            'q3'    : 0.002499134*1000,    # Third quartile (75th percentile)
            'whishi': 0.005254277*1000,    # Top whisker position
            'fliers': []        # Outliers
        },
        
        {
            'label' : "CAV2 Local Fusion",
            'whislo': 0.001557977*1000,    # Bottom whisker position
            'q1'    : 0.001666448*1000,    # First quartile (25th percentile)
            'med'   : 0.001784964*1000,    # Median         (50th percentile)
            'q3'    : 0.002162773*1000,    # Third quartile (75th percentile)
            'whishi': 0.004475088*1000,    # Top whisker position
            'fliers': []        # Outliers
        },
        
        {
            'label' : "CAV1 Motor Actuation",
            'whislo': 0.00098301*1000,    # Bottom whisker position
            'q1'    : 0.001247511*1000,    # First quartile (25th percentile)
            'med'   : 0.001596355*1000,    # Median         (50th percentile)
            'q3'    : 0.00243028*1000,    # Third quartile (75th percentile)
            'whishi': 0.004871802*1000,    # Top whisker position
            'fliers': []        # Outliers
        },
        
        {
            'label' : "CAV2 Motor Actuation",
            'whislo': 0.000958504*1000,    # Bottom whisker position
            'q1'    : 0.001198536*1000,    # First quartile (25th percentile)
            'med'   : 0.001509895*1000,    # Median         (50th percentile)
            'q3'    : 0.002251959*1000,    # Third quartile (75th percentile)
            'whishi': 0.004548487*1000,    # Top whisker position
            'fliers': []        # Outliers
        }
        # ,
        
        # {
        #     'label' : "RSU Global Fusion",
        #     'whislo': 0.001000166*1000,    # Bottom whisker position
        #     'q1'    : 0.001000643*1000,    # First quartile (25th percentile)
        #     'med'   : 0.001509895*1000,    # Median         (50th percentile)
        #     'q3'    : 0.002251959*1000,    # Third quartile (75th percentile)
        #     'whishi': 0.004548487*1000,    # Top whisker position
        #     'fliers': []        # Outliers
        # },
        
        # {
        #     'label' : "RSU Vehicle Updates",
        #     'whislo': 0.001000166*1000,    # Bottom whisker position
        #     'q1'    : 0.001000643*1000,    # First quartile (25th percentile)
        #     'med'   : 0.001000881*1000,    # Median         (50th percentile)
        #     'q3'    : 0.001002034*1000,    # Third quartile (75th percentile)
        #     'whishi': 0.00200379*1000,    # Top whisker position
        #     'fliers': []        # Outliers
        # }
    ]

    make_boxplot(boxes)

def plot_second_test_results():

    boxes = [
        {
            'label' : "CAV1 Local Fusion",
            'whislo': 0.00158267*1000,    # Bottom whisker position
            'q1'    : 0.001683235*1000,    # First quartile (25th percentile)
            'med'   : 0.001816392*1000,    # Median         (50th percentile)
            'q3'    : 0.002269089*1000,    # Third quartile (75th percentile)
            'whishi': 0.004987097*1000,    # Top whisker position
            'fliers': []        # Outliers
        }
        ,
        {
            'label' : "CAV2 Local Fusion",
            'whislo': 0.001551652*1000,    # Bottom whisker position
            'q1'    : 0.001660585*1000,    # First quartile (25th percentile)
            'med'   : 0.001780033*1000,    # Median         (50th percentile)
            'q3'    : 0.002193928*1000,    # Third quartile (75th percentile)
            'whishi': 0.004455364*1000,    # Top whisker position
            'fliers': []        # Outliers
        }
        ,
        {
            'label' : "CAV1 Motor Actuation",
            'whislo': 0.000994229*1000,    # Bottom whisker position
            'q1'    : 0.00124526*1000,    # First quartile (25th percentile)
            'med'   : 0.001547098*1000,    # Median         (50th percentile)
            'q3'    : 0.002298117*1000,    # Third quartile (75th percentile)
            'whishi': 0.004818177*1000,    # Top whisker position
            'fliers': []        # Outliers
        }
        ,
        {
            'label' : "CAV2 Motor Actuation",
            'whislo': 0.000980854*1000,    # Bottom whisker position
            'q1'    : 0.001231909*1000,    # First quartile (25th percentile)
            'med'   : 0.001546621*1000,    # Median         (50th percentile)
            'q3'    : 0.002271175*1000,    # Third quartile (75th percentile)
            'whishi': 0.004535818*1000,    # Top whisker position
            'fliers': []        # Outliers
        }
        , 
        {
            'label' : "RSU Global Fusion",
            'whislo': 0.001418078*1000,    # Bottom whisker position
            'q1'    : 0.001508653*1000,    # First quartile (25th percentile)
            'med'   : 0.00156951*1000,    # Median         (50th percentile)
            'q3'    : 0.001639485*1000,    # Third quartile (75th percentile)
            'whishi': 0.001784039*1000,    # Top whisker position
            'fliers': []        # Outliers
        },
        

    ]

    make_boxplot(boxes)

def main(test=2): 
    if test==1:
        plot_first_test_results()
    elif test==2:
        plot_second_test_results()

if __name__ == "__main__":
    main()