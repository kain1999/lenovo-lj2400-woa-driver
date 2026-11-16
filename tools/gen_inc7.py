#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_inc7.py — A12a: 极简 Duplex(单选项); A12b: feature 改名 MyDuplex"""
import os

B = r"E:\Deepseek\lj2400woa\build\inc2\A3a_enname.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc7"
os.makedirs(OUT, exist_ok=True)

base = open(B, encoding="gbk").read()

a12a = base + '''
*Feature: Duplex
{
    *DefaultOption: SIMPLEX
    *Name: "Duplex"
    *Option: SIMPLEX
    {
        *Name: "Simplex"
    }
}
'''

a12b = base + '''
*Feature: MyDuplex
{
    *DefaultOption: OneSided
    *Name: "MyDuplex"
    *Option: OneSided
    {
        *Name: "None"
    }
    *Option: TwoSided
    {
        *Name: "Two"
    }
}
'''

open(os.path.join(OUT, "A12a_mindup.gpd"), "w", encoding="ascii", newline="\r\n").write(a12a)
open(os.path.join(OUT, "A12b_mydup.gpd"), "w", encoding="ascii", newline="\r\n").write(a12b)
print("OK A12a/A12b", len(a12a), len(a12b))
