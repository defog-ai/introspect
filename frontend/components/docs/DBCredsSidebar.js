import { AutoComplete, Button, Input, Select } from "antd";
import React, { useContext, useEffect, useRef, useState } from "react";
import { DocContext } from "./DocContext";

export function DBCredsSidebar() {
  const docContext = useContext(DocContext);
  const [disabled, setDisabled] = useState(true);
  const ctr = useRef(null);

  // autocomplete fires onSelect event with new value before setting the input value
  // so we can't just use input value because it's not updated yet
  function checkChanged(newDbType = null) {
    const inputs = ctr.current.querySelectorAll(".ant-input");

    for (let i = 0; i < inputs.length; i++) {
      if (inputs[i].name === "dbType" && typeof newDbType === "string") {
        if (docContext.val.dbCreds[inputs[i].name] !== newDbType) {
          setDisabled(false);
          return;
        }
        continue;
      }

      if (docContext.val.dbCreds[inputs[i].name] !== inputs[i].value) {
        setDisabled(false);
        return;
      }
    }

    setDisabled(true);
  }

  function updateDbCreds() {
    if (!ctr.current) return;
    const inputs = Array.from(ctr.current.querySelectorAll(".ant-input"));

    const newCreds = { hasCreds: true };
    inputs.forEach((input) => {
      newCreds[input.name] = input.value;
      checkChanged({ target: input });
    });

    docContext.update({
      ...docContext.val,
      dbCreds: newCreds,
    });

    setDisabled(true);
  }

  return (
    <div className="sidebar" id="db-creds-sidebar">
      <div className="sidebar-content" ref={ctr}>
        <p className="small">Enter your DB credentials below and hit save.</p>

        <Input
          addonBefore="Database name"
          defaultValue={docContext.val.dbCreds.database}
          placeholder="Enter database name"
          onChange={checkChanged}
          name="database"
        ></Input>
        <Input
          addonBefore="Host"
          defaultValue={docContext.val.dbCreds.host}
          placeholder="Enter host"
          onChange={checkChanged}
          name="host"
        ></Input>

        <AutoComplete
          style={{ width: "100%" }}
          options={[
            { label: "Postgres", value: "postgres" },
            { label: "Redshift", value: "redshift" },
          ]}
          onSelect={checkChanged}
        >
          <Input
            addonBefore="DB type"
            defaultValue={docContext.val.dbCreds.host}
            placeholder="Enter database type"
            name="dbType"
            onChange={checkChanged}
          ></Input>
        </AutoComplete>

        <Input
          addonBefore="Port"
          defaultValue={docContext.val.dbCreds.port}
          placeholder="Enter port"
          onChange={checkChanged}
          name="port"
        ></Input>

        <Input
          addonBefore="User"
          defaultValue={docContext.val.dbCreds.user}
          placeholder="Enter user"
          onChange={checkChanged}
          name="user"
        ></Input>
        <Input
          addonBefore="Password"
          defaultValue={docContext.val.dbCreds.password}
          placeholder="Enter password"
          onChange={checkChanged}
          name="password"
        ></Input>
        <Button
          size="small"
          type="primary"
          disabled={disabled}
          onClick={updateDbCreds}
        >
          Save
        </Button>
      </div>
    </div>
  );
}
