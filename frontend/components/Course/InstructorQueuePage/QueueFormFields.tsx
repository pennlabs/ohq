import { useEffect, useMemo, useState } from "react";
import { Form, Icon, Popup } from "semantic-ui-react";
import { Queue, VideoChatSetting } from "../../../types";

export interface QueueFormInput {
    name: string;
    description: string;
    questionTemplate: string;
    queueId?: number;
    videoChatSetting: VideoChatSetting;
    pinEnabled: boolean;
    rateLimitEnabled: boolean;
    rateLimitLength?: number;
    rateLimitQuestions?: number;
    rateLimitMinutes?: number;
    questionTimerEnabled: boolean;
    questionTimerStartTime?: number;
}
interface QueueFormSettingsProps {
    defaultValues: any;
    queue?: Queue;
    loading: boolean;
    setInput: (any) => void;
    setDisabled: (boolean) => void;
}
enum RateLimitFields {
    RATE_LIMIT_QUESTIONS = "rateLimitQuestions",
    RATE_LIMIT_MINUTES = "rateLimitMinutes",
    RATE_LIMIT_LENGTH = "rateLimitLength",
}

enum QuestionTimerFields {
    QUESTION_TIMER_START_TIME = "questionTimerStartTime",
}

const castInt = (n: string): number | undefined => {
    let casted: number | undefined = parseInt(n, 10);
    if (isNaN(casted)) {
        casted = undefined;
    }

    return casted;
};

const QueueFormFields = ({
    defaultValues,
    queue,
    loading,
    setInput,
    setDisabled,
}: QueueFormSettingsProps) => {
    const input = defaultValues;
    const [validQuestionRate, setValidQuestionRate] = useState(true);
    const [validMinsRate, setValidMinsRate] = useState(true);
    const [validLenRate, setValidLenRate] = useState(true);

    const [validQuestionTime, setValidQuestionTime] = useState(true);
    const [nameCharCount, setNameCharCount] = useState(input.name.length);
    const [descCharCount, setDescCharCount] = useState(
        input.description.length
    );
    const [templCharCount, setTemplCharCount] = useState(
        input.questionTemplate.length
    );
    const descCharLimit: number = 1000;
    const templCharLimit: number = 1000;
    const isDisabled = useMemo(() => {
        let invalidInps = !input.name || !input.description;
        if (input.rateLimitEnabled) {
            invalidInps =
                invalidInps ||
                input.rateLimitLength === undefined ||
                (input.rateLimitLength !== undefined &&
                    input.rateLimitLength < 0);
            invalidInps =
                invalidInps ||
                input.rateLimitQuestions === undefined ||
                (input.rateLimitQuestions !== undefined &&
                    input.rateLimitQuestions <= 0);
            invalidInps =
                invalidInps ||
                input.rateLimitMinutes === undefined ||
                (input.rateLimitMinutes !== undefined &&
                    input.rateLimitMinutes <= 0);
        }
        if (input.questionTimerEnabled) {
            invalidInps =
                invalidInps ||
                input.questionTimerStartTime === undefined ||
                input.questionTimerStartTime <= 0;
        }
        if (!queue) return invalidInps;

        let isSame =
            input.name === queue.name &&
            input.description === queue.description &&
            input.questionTemplate === queue.questionTemplate &&
            input.videoChatSetting === queue.videoChatSetting &&
            input.pinEnabled === queue.pinEnabled;
        if (input.rateLimitEnabled !== queue.rateLimitEnabled) {
            isSame = false;
        } else if (input.rateLimitEnabled && queue.rateLimitEnabled) {
            isSame =
                isSame &&
                input.rateLimitLength === queue.rateLimitLength &&
                input.rateLimitQuestions === queue.rateLimitQuestions &&
                input.rateLimitMinutes === queue.rateLimitMinutes;
        }
        // TODO: this is probably bad
        if (input.questionTimerEnabled !== queue.questionTimerEnabled) {
            isSame = false;
        } else if (input.questionTimerEnabled && queue.questionTimerEnabled) {
            isSame =
                isSame &&
                input.questionTimerStartTime === queue.questionTimerStartTime;
        }
        return invalidInps || isSame;
        // Queue covers all our cases
        // TODO: Should make this not depend on "stringifying" queue, as it re-renders every time.
        // eslint-disable-next-line
    }, [input, JSON.stringify(queue)]);
    useEffect(() => {
        setDisabled(isDisabled);
    }, [isDisabled, setDisabled]);

    /* HANDLER FUNCTIONS */
    const handleInputChange = (e, { name, value }) => {
        if (name === "description" && value.length > descCharLimit) return;
        if (name === "questionTemplate" && value.length > templCharLimit)
            return;
        if (name === "name" && value.length > 100) return;

        input[name] = value;

        if (name === RateLimitFields.RATE_LIMIT_QUESTIONS) {
            input[name] = castInt(input[name]);
            setValidQuestionRate(input[name] > 0);
        }

        if (name === RateLimitFields.RATE_LIMIT_MINUTES) {
            input[name] = castInt(input[name]);
            setValidMinsRate(input[name] > 0);
        }

        if (name === RateLimitFields.RATE_LIMIT_LENGTH) {
            input[name] = castInt(input[name]);
            setValidLenRate(input[name] >= 0);
        }

        if (name === QuestionTimerFields.QUESTION_TIMER_START_TIME) {
            input[name] = castInt(input[name]);
            setValidQuestionTime(input[name] > 0);
        }

        setInput({ ...input });
        setDescCharCount(input.description.length);
        setTemplCharCount(input.questionTemplate.length);
        setNameCharCount(input.name.length);
    };

    const handleVideoChatInputChange = (e, { name }) => {
        switch (name) {
            case "videoChatRequired":
                input.videoChatSetting = VideoChatSetting.REQUIRED;
                break;
            case "videoChatOptional":
                input.videoChatSetting = VideoChatSetting.OPTIONAL;
                break;
            case "videoChatDisabled":
                input.videoChatSetting = VideoChatSetting.DISABLED;
                break;
        }
        setInput({ ...input });
    };
    /* PROPS UPDATE */

    return (
        <>
            <Form.Field required>
                <label htmlFor="form-name">Name</label>
                <Form.Input
                    id="form-name"
                    defaultValue={input.name}
                    name="name"
                    disabled={loading}
                    onChange={handleInputChange}
                />
                <div
                    style={{
                        textAlign: "right",
                        color: nameCharCount < 100 ? "" : "crimson",
                    }}
                >
                    {`Characters: ${nameCharCount}/100`}
                </div>
            </Form.Field>
            <Form.Field required>
                <label htmlFor="form-desc">Description</label>
                <Form.TextArea
                    id="form-desc"
                    defaultValue={input.description}
                    name="description"
                    disabled={loading}
                    onChange={handleInputChange}
                />
                <div
                    style={{
                        textAlign: "right",
                        color: descCharCount < descCharLimit ? "" : "crimson",
                    }}
                >
                    {`Characters: ${descCharCount}/${descCharLimit}`}
                </div>
            </Form.Field>
            <Form.Field>
                <label htmlFor="form-desc">Question Template</label>
                <Form.TextArea
                    id="form-desc"
                    defaultValue={input.questionTemplate}
                    name="questionTemplate"
                    disabled={loading}
                    onChange={handleInputChange}
                />
                <div
                    style={{
                        textAlign: "right",
                        color: templCharCount < templCharLimit ? "" : "crimson",
                    }}
                >
                    {`Characters: ${templCharCount}/${templCharLimit}`}
                </div>
            </Form.Field>
            <Form.Field>
                <label style={{ display: "inline-block" }} htmlFor="pin-toggle">
                    Pin
                </label>
                <Form.Radio
                    label="Enable Pin"
                    checked={input.pinEnabled}
                    name="pinEnabled"
                    id="pin-toggle"
                    toggle
                    disabled={loading}
                    onClick={() =>
                        setInput({
                            ...input,
                            pinEnabled: !input.pinEnabled,
                        })
                    }
                />
            </Form.Field>

            <Form.Field>
                <label
                    style={{ display: "inline-block" }}
                    htmlFor="rate-limit-toggle"
                >
                    Rate Limit
                </label>
                <Form.Radio
                    name="rateLimitEnabled"
                    id="rate-limit-toggle"
                    toggle
                    checked={input.rateLimitEnabled}
                    label="Enable queue rate-limiting"
                    onClick={() =>
                        setInput({
                            ...input,
                            rateLimitEnabled: !input.rateLimitEnabled,
                        })
                    }
                />

                {input.rateLimitEnabled && (
                    <Form.Group
                        id="rate-limit"
                        style={{
                            alignItems: "center",
                            marginLeft: "1em",
                        }}
                    >
                        <Form.Input
                            placeholder="3"
                            name={RateLimitFields.RATE_LIMIT_QUESTIONS}
                            defaultValue={input.rateLimitQuestions}
                            onChange={handleInputChange}
                            width={2}
                            size="mini"
                            type="number"
                            min="1"
                            id="rate-questions"
                            error={!validQuestionRate}
                        />
                        <label htmlFor="rate-questions">
                            question(s) within{" "}
                        </label>
                        <Form.Input
                            placeholder="60"
                            name={RateLimitFields.RATE_LIMIT_MINUTES}
                            defaultValue={input.rateLimitMinutes}
                            width={2}
                            size="mini"
                            onChange={handleInputChange}
                            type="number"
                            min="1"
                            id="rate-minutes"
                            error={!validMinsRate}
                        />
                        <label htmlFor="rate-minutes">
                            minutes per student when queue has at least
                        </label>
                        <Form.Input
                            placeholder="10"
                            name={RateLimitFields.RATE_LIMIT_LENGTH}
                            defaultValue={input.rateLimitLength}
                            width={2}
                            onChange={handleInputChange}
                            size="mini"
                            type="number"
                            min="0"
                            id="rate-length"
                            error={!validLenRate}
                        />
                        <label htmlFor="rate-length">question(s)</label>
                    </Form.Group>
                )}
                <Form.Field>
                    <label htmlFor="video-radio">Video Chat</label>
                    <Form.Group id="video-radio">
                        <Form.Radio
                            label="Require Link"
                            checked={
                                input.videoChatSetting ===
                                VideoChatSetting.REQUIRED
                            }
                            name="videoChatRequired"
                            disabled={loading}
                            onChange={handleVideoChatInputChange}
                        />
                        <Form.Radio
                            label="Allow Link"
                            checked={
                                input.videoChatSetting ===
                                VideoChatSetting.OPTIONAL
                            }
                            name="videoChatOptional"
                            disabled={loading}
                            onChange={handleVideoChatInputChange}
                        />
                        <Form.Radio
                            label="No Link"
                            checked={
                                input.videoChatSetting ===
                                VideoChatSetting.DISABLED
                            }
                            name="videoChatDisabled"
                            disabled={loading}
                            onChange={handleVideoChatInputChange}
                        />
                    </Form.Group>
                </Form.Field>
                <Form.Field>
                    <Popup
                        trigger={
                            <label
                                style={{ display: "inline-block" }}
                                htmlFor="timer-questions-group"
                            >
                                Question Timer
                                <Icon
                                    name="question circle outline"
                                    style={{ marginLeft: "0.5em" }}
                                />
                            </label>
                        }
                        content="The countdown timer is only visable to staff"
                    />

                    <Form.Radio
                        name="questionTimerEnabled"
                        defaultChecked={input.questionTimerEnabled}
                        toggle
                        label="Enable a countdown for questions"
                        onChange={() =>
                            setInput({
                                ...input,
                                questionTimerEnabled:
                                    !input.questionTimerEnabled,
                            })
                        }
                    />
                </Form.Field>

                {input.questionTimerEnabled && (
                    <Form.Group
                        id="timer-questions-group"
                        style={{
                            alignItems: "center",
                            marginLeft: "1em",
                        }}
                    >
                        <label id="timer-questions-group">
                            Countdown from{" "}
                        </label>
                        <Form.Input
                            placeholder="10"
                            name={QuestionTimerFields.QUESTION_TIMER_START_TIME}
                            defaultValue={input.questionTimerStartTime}
                            onChange={handleInputChange}
                            width={2}
                            size="mini"
                            type="number"
                            onKeyPress={(event) => {
                                if (!/[0-9]/.test(event.key)) {
                                    event.preventDefault();
                                }
                            }}
                            min="1"
                            id="timer-questions"
                            error={!validQuestionTime}
                        />
                        <label htmlFor="timer-questions">
                            minute(s) per question
                        </label>
                    </Form.Group>
                )}
            </Form.Field>
        </>
    );
};

export default QueueFormFields;
