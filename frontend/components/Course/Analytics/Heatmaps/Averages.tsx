import { Tab, Segment, Header } from "semantic-ui-react";
import { useHeatmapData } from "../../../../hooks/data-fetching/analytics";
import { HeatmapSeries, Metric } from "../../../../types";
import Heatmap from "./Heatmap";

interface AveragesProps {
    courseId: number;
    queueId: number;
    isStaff: boolean;
}

const QuestionsPerInstructorPane = (
    questionsData: HeatmapSeries[],
    questionsValidating: boolean
) => {
    return {
        menuItem: "Questions per Instructor",
        render: () => {
            if (questionsData) {
                return (
                    <Heatmap
                        series={questionsData}
                        chartTitle="Average Questions per Instructor"
                    />
                );
            }
            if (questionsValidating) {
                return <div>Loading...</div>;
            }
            return <div>Error loading data</div>;
        },
    };
};

const StudentWaitTimesPane = (
    waitTimesData: HeatmapSeries[],
    waitValidating: boolean
) => {
    return {
        menuItem: "Student Wait Times",
        render: () => {
            if (waitTimesData) {
                return (
                    <Heatmap
                        series={waitTimesData}
                        chartTitle="Average Student Wait Times in Minutes"
                    />
                );
            }
            if (waitValidating) return <div>Loading...</div>;
            return <div>Error loading data</div>;
        },
    };
};

export default function Averages({
    courseId,
    queueId,
    isStaff,
}: AveragesProps) {
    const { data: questionsData, isValidating: questionsValidating } =
        useHeatmapData(courseId, queueId, Metric.HEATMAP_QUESTIONS);
    const { data: waitTimesData, isValidating: waitValidating } =
        useHeatmapData(courseId, queueId, Metric.HEATMAP_WAIT);

    return (
        <Segment padded>
            <Header as="h3">Semester Averages</Header>
            <Tab
                menu={{ secondary: true, pointing: true }}
                panes={[
                    ...(isStaff
                        ? [
                              QuestionsPerInstructorPane(
                                  questionsData || [],
                                  questionsValidating
                              ),
                          ]
                        : []),
                    StudentWaitTimesPane(waitTimesData || [], waitValidating),
                ]}
            />
        </Segment>
    );
}
