# calc_within_bucket_variation produces expected results

    Code
      round(calc_within_bucket_variation(mv, "accuracy"), 10)
    Output
         mv_dim_A    mv_dim_B    mv_dim_C 
      0.010123810 0.002658333 0.000587500 

# calc_between_bucket_variation produces expected results

    Code
      round(calc_between_bucket_variation(mv, "accuracy"), 10)
    Output
       mv_dim_A  mv_dim_B  mv_dim_C 
      0.0185625 0.0043125 0.0005875 

