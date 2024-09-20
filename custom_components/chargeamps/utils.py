from dataclasses import field
from datetime import datetime
from typing import Optional

from ciso8601 import parse_datetime
from dataclasses_json import config
from marshmallow import fields


def datetime_encoder(x: Optional[datetime]) -> Optional[str]:
    return datetime.isoformat(x) if x is not None else None


def datetime_decoder(x: Optional[str]) -> Optional[datetime]:
    return parse_datetime(x) if x is not None else None


def datetime_field():
    return field(
        default=None,
        metadata=config(
            encoder=datetime_encoder,
            decoder=datetime_decoder,
            mm_field=fields.DateTime(format="iso"),
        ),
    )
