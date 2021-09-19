import React from "react";
import { Button, Modal } from "semantic-ui-react";
import Changelog from "../../../Changelog";

interface ModalShowNewChangesProps {
    openModal: boolean;
    setOpen: (boolean) => void;
}

const ModalShowNewChanges = (props: ModalShowNewChangesProps) => {
    const { openModal, setOpen } = props;
    return (
        <Modal open={openModal} size="large">
            <Modal.Content scrolling>
                <Changelog />
            </Modal.Content>
            <Modal.Actions>
                <Button onClick={() => setOpen(false)}>Close</Button>
            </Modal.Actions>
        </Modal>
    );
};

export default ModalShowNewChanges;
