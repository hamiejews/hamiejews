import logging
import guardrails as gd
from datetime import date
from .run_type import RunMode
from pydantic import BaseModel, Field
from guardrails.validators import ValidChoices
from typing import List, Callable, Dict, Union, Any, Tuple
from .prompts import (
    short_memory_id_desc,
    mid_memory_id_desc,
    long_memory_id_desc,
    reflection_memory_id_desc,
    train_prompt,
    train_memory_id_extract_prompt,
    train_trade_reason_summary,
    train_investment_info_prefix,
    test_prompt,
    test_trade_reason_summary,
    test_memory_id_extract_prompt,
    test_invest_action_choice,
    test_investment_info_prefix,
    test_sentiment_explanation,
    test_momentum_explanation,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler = logging.FileHandler("run.log", mode="a")
file_handler.setFormatter(logging_formatter)
logger.addHandler(file_handler)


def _train_memory_factory(memory_layer: str, id_list: List[int]):
    class Memory(BaseModel):
        memory_index: int = Field(
            ...,
            description=train_memory_id_extract_prompt.format(
                memory_layer=memory_layer
            ),
            validators=[ValidChoices(id_list, on_fail="reask")],  # type: ignore
        )

    return Memory


def _test_memory_factory(memory_layer: str, id_list: List[int]):
    class Memory(BaseModel):
        memory_index: int = Field(
            ...,
            description=test_memory_id_extract_prompt.format(memory_layer=memory_layer),
            validators=[ValidChoices(id_list)],  # type: ignore
        )

    return Memory


# train + test reflection model
def _train_reflection_factory(
    short_id_list: List[int],
    mid_id_list: List[int],
    long_id_list: List[int],
    reflection_id_list: List[int],
):
    LongMem = _train_memory_factory("long-level", long_id_list)
    MidMem = _train_memory_factory("mid-level", mid_id_list)
    ShortMem = _train_memory_factory("short-level", short_id_list)
    ReflectionMem = _train_memory_factory("reflection-level", reflection_id_list)

    class InvestInfo(BaseModel):
        if reflection_id_list:
            reflection_memory_index: List[ReflectionMem] = Field(
                ...,
                description=reflection_memory_id_desc,
            )
        if long_id_list:
            long_memory_index: List[LongMem] = Field(
                ...,
                description=long_memory_id_desc,
            )
        if mid_id_list:
            middle_memory_index: List[MidMem] = Field(
                ...,
                description=mid_memory_id_desc,
            )
        if short_id_list:
            short_memory_index: List[ShortMem] = Field(
                ...,
                description=short_memory_id_desc,
            )
        summary_reason: str = Field(
            ...,
            description=train_trade_reason_summary,
        )

    return InvestInfo


def _test_reflection_factory(
    short_id_list: List[int],
    mid_id_list: List[int],
    long_id_list: List[int],
    reflection_id_list: List[int],
):
    LongMem = _test_memory_factory("long-level", long_id_list)
    MidMem = _test_memory_factory("mid-level", mid_id_list)
    ShortMem = _test_memory_factory("short-level", short_id_list)
    ReflectionMem = _test_memory_factory("reflection-level", reflection_id_list)

    class InvestInfo(BaseModel):
        investment_decision: str = Field(
            ...,
            description=test_invest_action_choice,
            validators=[ValidChoices(choices=["buy", "sell", "hold"])],  # type: ignore
        )
        summary_reason: str = Field(
            ...,
            description=test_trade_reason_summary,
        )
        if short_id_list:
            short_memory_index: List[ShortMem] = Field(
                ...,
                description=short_memory_id_desc,
            )
        if mid_id_list:
            middle_memory_index: List[MidMem] = Field(
                ...,
                description=mid_memory_id_desc,
            )
        if long_id_list:
            long_memory_index: List[LongMem] = Field(
                ...,
                description=long_memory_id_desc,
            )
        if reflection_id_list:
            reflection_memory_index: List[ReflectionMem] = Field(
                ...,
                description=reflection_memory_id_desc,
            )

    return InvestInfo


def _format_memories(
    short_memory: Union[List[str], None] = None,
    short_memory_id: Union[List[int], None] = None,
    mid_memory: Union[List[str], None] = None,
    mid_memory_id: Union[List[int], None] = None,
    long_memory: Union[List[str], None] = None,
    long_memory_id: Union[List[int], None] = None,
    reflection_memory: Union[List[str], None] = None,
    reflection_memory_id: Union[List[int], None] = None,
) -> Tuple[
    List[str],
    List[int],
    List[str],
    List[int],
    List[str],
    List[int],
    List[str],
    List[int],
]:
    # add placeholder if no memory
    if (short_memory is None) or len(short_memory) == 0:
        short_memory = ["No short-term information.", "No short-term information."]
        short_memory_id = [-1, -1]
    else:
        short_memory = [short_memory[0], short_memory[0]]
        short_memory_id = [short_memory_id[0], short_memory_id[0]]  # type: ignore
    if (mid_memory is None) or len(mid_memory) == 0:
        mid_memory = ["No mid-term information.", "No mid-term information."]
        mid_memory_id = [-1, -1]
    else:
        mid_memory = [mid_memory[0], mid_memory[0]]
        mid_memory_id = [mid_memory_id[0], mid_memory_id[0]]  # type: ignore
    if (long_memory is None) or len(long_memory) == 0:
        long_memory = ["No long-term information.", "No long-term information."]
        long_memory_id = [-1, -1]
    else:
        long_memory = [long_memory[0], long_memory[0]]
        long_memory_id = [long_memory_id[0], long_memory_id[0]]  # type: ignore
    if (reflection_memory is None) or len(reflection_memory) == 0:
        reflection_memory = [
            "No reflection-term information.",
            "No reflection-term information.",
        ]
        reflection_memory_id = [-1, -1]
    else:
        reflection_memory = [reflection_memory[0], reflection_memory[0]]
        reflection_memory_id = [reflection_memory_id[0], reflection_memory_id[0]]  # type: ignore

    return (
        short_memory,
        short_memory_id,
        mid_memory,
        mid_memory_id,
        long_memory,
        long_memory_id,
        reflection_memory,
        reflection_memory_id,
    )


def _delete_placeholder_info(validated_output: Dict[str, Any]) -> Dict[str, Any]:
    if (validated_output["reflection_memory_index"]) and (
        validated_output["reflection_memory_index"][0]["memory_index"] == -1
    ):
        del validated_output["reflection_memory_index"]
    if (validated_output["long_memory_index"]) and (
        validated_output["long_memory_index"][0]["memory_index"] == -1
    ):
        del validated_output["long_memory_index"]
    if (validated_output["middle_memory_index"]) and (
        validated_output["middle_memory_index"][0]["memory_index"] == -1
    ):
        del validated_output["middle_memory_index"]
    if (validated_output["short_memory_index"]) and (
        validated_output["short_memory_index"][0]["memory_index"] == -1
    ):
        del validated_output["short_memory_index"]

    return validated_output


def _add_momentum_info(momentum: int, investment_info: str) -> str:
    """
    Add text about momentum (positive, negative, or zero) to the reflection output.
    """
    if momentum == -1:
        investment_info += "The cumulative return of the past few days for this asset is negative."

    elif momentum == 0:
        investment_info += "The cumulative return of the past few days for this asset is zero."

    elif momentum == 1:
        investment_info += "The cumulative return of the past few days for this asset is positive."

    return investment_info


def _train_response_model_invest_info(
    cur_date: date,
    symbol: str,
    future_record: Dict[str, float | str],
    short_memory: List[str],
    short_memory_id: List[int],
    mid_memory: List[str],
    mid_memory_id: List[int],
    long_memory: List[str],
    long_memory_id: List[int],
    reflection_memory: List[str],
    reflection_memory_id: List[int],
):
    # pydantic reflection model
    response_model = _train_reflection_factory(
        short_id_list=short_memory_id,
        mid_id_list=mid_memory_id,
        long_id_list=long_memory_id,
        reflection_id_list=reflection_memory_id,
    )
    # investment info + memories
    investment_info = train_investment_info_prefix.format(
        cur_date=cur_date, symbol=symbol, future_record=future_record
    )
    if short_memory:
        investment_info += "The short-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(short_memory_id, short_memory)]
        )
        investment_info += "\n\n"
    if mid_memory:
        investment_info += "The mid-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(mid_memory_id, mid_memory)]
        )
        investment_info += "\n\n"
    if long_memory:
        investment_info += "The long-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(long_memory_id, long_memory)]
        )
        investment_info += "\n\n"
    if reflection_memory:
        investment_info += "The reflection-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1]}" for i in enumerate(reflection_memory, 1)]
        )
        investment_info += "\n\n"

    return response_model, investment_info


def _test_response_model_invest_info(
    cur_date: date,
    symbol: str,
    short_memory: List[str],
    short_memory_id: List[int],
    mid_memory: List[str],
    mid_memory_id: List[int],
    long_memory: List[str],
    long_memory_id: List[int],
    reflection_memory: List[str],
    reflection_memory_id: List[int],
    momentum: Union[int, None] = None,
):
    # pydantic reflection model
    response_model = _test_reflection_factory(
        short_id_list=short_memory_id,
        mid_id_list=mid_memory_id,
        long_id_list=long_memory_id,
        reflection_id_list=reflection_memory_id,
    )
    # investment info + memories
    investment_info = test_investment_info_prefix.format(
        symbol=symbol, cur_date=cur_date
    )
    if short_memory:
        investment_info += "The short-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(short_memory_id, short_memory)]
        )
        investment_info += test_sentiment_explanation
        investment_info += "\n\n"
    if mid_memory:
        investment_info += "The mid-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(mid_memory_id, mid_memory)]
        )
        investment_info += "\n\n"
    if long_memory:
        investment_info += "The long-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1].strip()}" for i in zip(long_memory_id, long_memory)]
        )
        investment_info += "\n\n"
    if reflection_memory:
        investment_info += "The reflection-term information:\n"
        investment_info += "\n".join(
            [f"{i[0]}. {i[1]}" for i in enumerate(reflection_memory, 1)]
        )
        investment_info += "\n\n"
    if momentum:
        investment_info += test_momentum_explanation
        investment_info = _add_momentum_info(momentum, investment_info)

    return response_model, investment_info


def trading_reflection(
    cur_date: date,
    endpoint_func: Callable[[str], str],
    symbol: str,
    run_mode: RunMode,
    momentum: Union[int, None] = None,
    future_record: Union[Dict[str, float | str], None] = None,
    short_memory: Union[List[str], None] = None,
    short_memory_id: Union[List[int], None] = None,
    mid_memory: Union[List[str], None] = None,
    mid_memory_id: Union[List[int], None] = None,
    long_memory: Union[List[str], None] = None,
    long_memory_id: Union[List[int], None] = None,
    reflection_memory: Union[List[str], None] = None,
    reflection_memory_id: Union[List[int], None] = None,
) -> Dict[str, Any]:
    # format memories
    (
        short_memory,
        short_memory_id,
        mid_memory,
        mid_memory_id,
        long_memory,
        long_memory_id,
        reflection_memory,
        reflection_memory_id,
    ) = _format_memories(
        short_memory=short_memory,
        short_memory_id=short_memory_id,
        mid_memory=mid_memory,
        mid_memory_id=mid_memory_id,
        long_memory=long_memory,
        long_memory_id=long_memory_id,
        reflection_memory=reflection_memory,
        reflection_memory_id=reflection_memory_id,
    )

    if run_mode == RunMode.Train:
        response_model, investment_info = _train_response_model_invest_info(
            cur_date=cur_date,
            symbol=symbol,
            future_record=future_record,  # type: ignore
            short_memory=short_memory,
            short_memory_id=short_memory_id,
            mid_memory=mid_memory,
            mid_memory_id=mid_memory_id,
            long_memory=long_memory,
            long_memory_id=long_memory_id,
            reflection_memory=reflection_memory,
            reflection_memory_id=reflection_memory_id,
        )
        cur_prompt = train_prompt
    else:
        response_model, investment_info = _test_response_model_invest_info(
            cur_date=cur_date,
            symbol=symbol,
            short_memory=short_memory,
            short_memory_id=short_memory_id,
            mid_memory=mid_memory,
            mid_memory_id=mid_memory_id,
            long_memory=long_memory,
            long_memory_id=long_memory_id,
            reflection_memory=reflection_memory,
            reflection_memory_id=reflection_memory_id,
            momentum=momentum,
        )
        cur_prompt = test_prompt

    # prompt + validated output
    guard = gd.Guard.from_pydantic(
        output_class=response_model, prompt=cur_prompt, num_reasks=2
    )
    _, validated_output = guard(
        endpoint_func,
        prompt_params={"investment_info": investment_info},
    )
    if (validated_output is None) or (not isinstance(validated_output, dict)):
        logger.info(f"reflection failed for {symbol}")
        return {}

    return _delete_placeholder_info(validated_output)
