from typing import Annotated, List, Literal, Optional

from fastapi import Form
from pydantic import BaseModel, BeforeValidator

from prepline_general.api.utils import SmartValueParser


class GeneralFormParams(BaseModel):
    """General partition API form parameters for the prepline API.
    To add a new parameter, add it here and in the as_form classmethod.
    Use Annotated to add a description and example for the parameter.
    """

    xml_keep_tags: bool
    languages: Optional[List[str]]
    ocr_languages: Optional[List[str]]
    skip_infer_table_types: Optional[List[str]]
    gz_uncompressed_content_type: Optional[str]
    output_format: str
    coordinates: bool
    encoding: str
    hi_res_model_name: Optional[str]
    include_page_breaks: bool
    pdf_infer_table_structure: bool
    strategy: str
    extract_image_block_types: Optional[List[str]]
    unique_element_ids: bool
    # -- chunking options --
    chunking_strategy: Optional[str]
    combine_under_n_chars: Optional[int]
    max_characters: int
    multipage_sections: bool
    new_after_n_chars: Optional[int]
    overlap: int
    overlap_all: bool
    starting_page_number: Optional[int] = None

    @classmethod
    def as_form(
        cls,
        xml_keep_tags: Annotated[
            bool,
            Form(
                title="Xml Keep Tags",
                description="If True, will retain the XML tags in the output. Otherwise it will simply extract the text from within the tags. Only applies to partition_xml.",
            ),
            BeforeValidator(SmartValueParser[bool]().value_or_first_element),
        ] = False,
        languages: Annotated[
            List[str],
            Form(
                title="OCR Languages",
                description="The languages present in the document, for use in partitioning and/or OCR",
                example="[eng]",
            ),
            BeforeValidator(SmartValueParser[List[str]]().value_or_first_element),
        ] = [],  # noqa
        ocr_languages: Annotated[
            List[str],
            Form(
                title="OCR Languages",
                description="The languages present in the document, for use in partitioning and/or OCR",
                example="[eng]",
            ),
            BeforeValidator(SmartValueParser[List[str]]().value_or_first_element),
        ] = [],
        skip_infer_table_types: Annotated[
            List[str],
            Form(
                title="Skip Infer Table Types",
                description=(
                    "The document types that you want to skip table extraction with. Default: []"
                ),
                example="['pdf', 'jpg', 'png']",
            ),
            BeforeValidator(SmartValueParser[List[str]]().value_or_first_element),
        ] = [],  # noqa
        gz_uncompressed_content_type: Annotated[
            Optional[str],
            Form(
                title="Uncompressed Content Type",
                description="If file is gzipped, use this content type after unzipping",
                example="application/pdf",
            ),
        ] = None,
        output_format: Annotated[
            Literal["application/json", "text/csv"],
            Form(
                title="Output Format",
                description="The format of the response. Supported formats are application/json and text/csv. Default: application/json.",
                example="application/json",
            ),
        ] = "application/json",
        coordinates: Annotated[
            bool,
            Form(
                title="Coordinates",
                description="If true, return coordinates for each element. Default: false",
            ),
            BeforeValidator(SmartValueParser[bool]().value_or_first_element),
        ] = False,
        encoding: Annotated[
            str,
            Form(
                title="Encoding",
                description="The encoding method used to decode the text input. Default: utf-8",
                example="utf-8",
            ),
            BeforeValidator(SmartValueParser[str]().value_or_first_element),
        ] = "utf-8",
        hi_res_model_name: Annotated[
            Optional[str],
            Form(
                title="Hi Res Model Name",
                description="The name of the inference model used when strategy is hi_res",
                example="yolox",
            ),
            BeforeValidator(SmartValueParser[str]().value_or_first_element),
        ] = None,
        include_page_breaks: Annotated[
            bool,
            Form(
                title="Include Page Breaks",
                description="If True, the output will include page breaks if the filetype supports it. Default: false",
            ),
            BeforeValidator(SmartValueParser[str]().value_or_first_element),
        ] = False,
        pdf_infer_table_structure: Annotated[
            bool,
            Form(
                title="Pdf Infer Table Structure",
                description=(
                    "Deprecated! Use skip_infer_table_types to opt out of table extraction for any "
                    "file type. If False and strategy=hi_res, no Table Elements will be extracted "
                    "from pdf files regardless of skip_infer_table_types contents."
                ),
            ),
            BeforeValidator(SmartValueParser[bool]().value_or_first_element),
        ] = True,
        strategy: Annotated[
            Literal["fast", "hi_res", "auto", "ocr_only"],
            Form(
                title="Strategy",
                description="The strategy to use for partitioning PDF/image. Options are fast, hi_res, auto. Default: auto",
                examples=["auto", "hi_res"],
            ),
            BeforeValidator(SmartValueParser[str]().value_or_first_element),
        ] = "auto",
        extract_image_block_types: Annotated[
            List[str],
            Form(
                title="Image block types to extract",
                description="The types of elements to extract, for use in extracting image blocks as base64 encoded data stored in metadata fields",
                example="""["image", "table"]""",
            ),
            BeforeValidator(SmartValueParser[List[str]]().value_or_first_element),
        ] = [],  # noqa
        unique_element_ids: Annotated[
            bool,
            Form(
                title="unique_element_ids",
                description="""When `True`, assign UUIDs to element IDs, which guarantees their uniqueness 
(useful when using them as primary keys in database). Otherwise a SHA-256 of element text is used. Default: False""",
                example=True,
            ),
        ] = False,
        # -- chunking options --
        chunking_strategy: Annotated[
            Optional[Literal["by_title"]],
            Form(
                title="Chunking Strategy",
                description="Use one of the supported strategies to chunk the returned elements. Currently supports: by_title",
                examples=["by_title"],
            ),
        ] = None,
        combine_under_n_chars: Annotated[
            Optional[int],
            Form(
                title="Combine Under N Chars",
                description="If chunking strategy is set, combine elements until a section reaches a length of n chars. Default: 500",
                example=500,
            ),
        ] = None,
        max_characters: Annotated[
            int,
            Form(
                title="Max Characters",
                description="If chunking strategy is set, cut off new sections after reaching a length of n chars (hard max). Default: 1500",
                example=1500,
            ),
        ] = 500,
        multipage_sections: Annotated[
            bool,
            Form(
                title="Multipage Sections",
                description="If chunking strategy is set, determines if sections can span multiple sections. Default: true",
            ),
        ] = True,
        new_after_n_chars: Annotated[
            Optional[int],
            Form(
                title="New after n chars",
                description="If chunking strategy is set, cut off new sections after reaching a length of n chars (soft max). Default: 1500",
                example=1500,
            ),
        ] = None,
        overlap: Annotated[
            int,
            Form(
                title="Overlap",
                description="""Specifies the length of a string ("tail") to be drawn from each chunk and prefixed to the
next chunk as a context-preserving mechanism. By default, this only applies to split-chunks
where an oversized element is divided into multiple chunks by text-splitting. Default: 0""",
                example=20,
            ),
        ] = 0,
        overlap_all: Annotated[
            bool,
            Form(
                title="Overlap all",
                description="""When `True`, apply overlap between "normal" chunks formed from whole
elements and not subject to text-splitting. Use this with caution as it entails a certain
level of "pollution" of otherwise clean semantic chunk boundaries. Default: False""",
                example=True,
            ),
        ] = False,
        starting_page_number: Annotated[
            Optional[int],
            Form(
                title="PDF Starting Page Number",
                description=(
                    "When PDF is split into pages before sending it into the API, providing "
                    "this information will allow the page number to be assigned correctly."
                ),
                example=3,
            ),
        ] = None,
    ) -> "GeneralFormParams":
        return cls(
            xml_keep_tags=xml_keep_tags,
            languages=languages if languages else None,
            ocr_languages=ocr_languages if ocr_languages else None,
            skip_infer_table_types=skip_infer_table_types,
            gz_uncompressed_content_type=gz_uncompressed_content_type,
            output_format=output_format,
            coordinates=coordinates,
            encoding=encoding,
            hi_res_model_name=hi_res_model_name,
            include_page_breaks=include_page_breaks,
            pdf_infer_table_structure=pdf_infer_table_structure,
            strategy=strategy,
            extract_image_block_types=(
                extract_image_block_types if extract_image_block_types else None
            ),
            chunking_strategy=chunking_strategy,
            combine_under_n_chars=combine_under_n_chars,
            max_characters=max_characters,
            multipage_sections=multipage_sections,
            new_after_n_chars=new_after_n_chars,
            overlap=overlap,
            overlap_all=overlap_all,
            unique_element_ids=unique_element_ids,
            starting_page_number=starting_page_number,
        )
