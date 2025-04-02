db.orders.aggregate([
    {
      $addFields: {
        day: {
          $substr: [
            "$order_purchase_timestamp",
            0, 
            10
          ]
        }
      }
    },
    { $group: { _id: "$day", order_count: { $sum: 1 } } },
    { $sort: { _id: 1 } },
    { $project: { _id: 0, day: "$_id", order_count: 1 } }
  ])