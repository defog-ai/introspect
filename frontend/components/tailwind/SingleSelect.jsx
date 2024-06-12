import {
  Combobox,
  ComboboxButton,
  ComboboxInput,
  ComboboxOption,
  ComboboxOptions,
  Label,
} from "@headlessui/react";
import { CheckIcon, ChevronUpDownIcon } from "@heroicons/react/20/solid";
import { useEffect, useState } from "react";
import { twMerge } from "tailwind-merge";

// const options = [
//   { id: 1, name: "Leslie Alexander" },
//   // More users...
// ];

export default function SingleSelect({
  rootClassName = "",
  popupClassName = "",
  onChange = null,
  defaultValue = null,
  options = [],
  label = null,
}) {
  const [query, setQuery] = useState("");

  const filteredOptions =
    query === ""
      ? options
      : options.filter((option) => {
          console.log(option);
          return (option.label + "")
            .toLowerCase()
            .includes(query.toLowerCase());
        });

  // find the option matching the default value
  const [selectedOption, setSelectedOption] = useState(
    options.find((option) => option.value === defaultValue)
  );

  return (
    <Combobox
      as="div"
      by="value"
      className={rootClassName}
      value={selectedOption}
      defaultValue={defaultValue}
      onChange={(option) => {
        setQuery("");
        setSelectedOption(option);
        if (option && onChange && typeof onChange === "function") {
          onChange(option);
        }
      }}
    >
      {label && (
        <Label className="block text-sm mb-2 font-medium leading-6 text-gray-900">
          Assigned to
        </Label>
      )}
      <div className="relative">
        <ComboboxInput
          className="w-full rounded-md border-0 bg-white py-1.5 pl-3 pr-10 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
          onChange={(event) => setQuery(event.target.value)}
          onBlur={() => setQuery("")}
          displayValue={(option) => option?.label}
        />
        <ComboboxButton className="absolute inset-y-0 right-0 flex items-center rounded-r-md px-2 focus:outline-none">
          <ChevronUpDownIcon
            className="h-5 w-5 text-gray-400"
            aria-hidden="true"
          />
        </ComboboxButton>

        {filteredOptions.length > 0 && (
          <ComboboxOptions
            className={twMerge(
              "z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm absolute bottom-10",
              popupClassName
            )}
          >
            {filteredOptions.map((option) => (
              <ComboboxOption
                key={option.value}
                value={option}
                className={({ focus }) =>
                  twMerge(
                    "relative cursor-default select-none py-2 pl-3 pr-9",
                    focus ? "bg-blue-400 text-white" : "text-gray-900"
                  )
                }
              >
                {({ focus, selected }) => (
                  <>
                    <span
                      className={twMerge(
                        "block truncate",
                        selected && "font-semibold"
                      )}
                    >
                      {option.label}
                    </span>

                    {selected && (
                      <span
                        className={twMerge(
                          "absolute inset-y-0 right-0 flex items-center pr-4",
                          focus ? "text-white" : "text-blue-400"
                        )}
                      >
                        <CheckIcon className="h-5 w-5" aria-hidden="true" />
                      </span>
                    )}
                  </>
                )}
              </ComboboxOption>
            ))}
          </ComboboxOptions>
        )}
      </div>
    </Combobox>
  );
}
